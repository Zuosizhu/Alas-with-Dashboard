import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import inflection
from cached_property import cached_property

from module.base.decorator import del_cached_property
from module.config.config import AzurLaneConfig, TaskEnd
from module.config.deep import deep_get, deep_set
from module.exception import *
from module.logger import logger
from module.notify import handle_notify
from module.ui.page import page_dorm, page_dormmenu, page_commission, page_research, page_guild, page_shop, page_main
from module.dorm.assets import DORM_RED_DOT


class AzurLaneAutoScript:
    stop_event: threading.Event = None

    def __init__(self, config_name='alas'):
        logger.hr('Start', level=0)
        self.config_name = config_name
        # Skip first restart
        self.is_first_task = True
        # Failure count of tasks
        # Key: str, task name, value: int, failure count
        self.failure_record = {}

    @cached_property
    def config(self):
        try:
            config = AzurLaneConfig(config_name=self.config_name)
            return config
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            sys.exit(1)
        except Exception as e:
            logger.exception(e)
            sys.exit(1)

    @cached_property
    def device(self):
        try:
            from module.device.device import Device
            device = Device(config=self.config)
            return device
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            sys.exit(1)
        except Exception as e:
            logger.exception(e)
            sys.exit(1)

    @cached_property
    def checker(self):
        try:
            from module.server_checker import ServerChecker
            checker = ServerChecker(server=self.config.Emulator_ServerName)
            return checker
        except Exception as e:
            logger.exception(e)
            sys.exit(1)

    @cached_property
    def ui(self):
        try:
            from module.ui.ui import UI
            ui = UI(self.config, device=self.device)
            return ui
        except Exception as e:
            logger.exception(e)
            sys.exit(1)

    @cached_property
    def state_machine(self):
        try:
            from module.state_machine import StateMachine
            state_machine = StateMachine(ui=self.ui)
            return state_machine
        except Exception as e:
            logger.exception(e)
            sys.exit(1)

    def cal_dorm_delay(self, ships):
        dict_delay = {
            0: self.config.Scheduler_SuccessInterval,
            1: 1000,
            2: 556,
            3: 417,
            4: 358,
            5: 313,
            6: 278,
        }
        delay = dict_delay.get(ships, self.config.Scheduler_SuccessInterval)
        return delay

    def run(self, command, skip_first_screenshot=False):
        try:
            if not skip_first_screenshot:
                self.device.screenshot()
            self.__getattribute__(command)()
            return True
        except TaskEnd:
            return True
        except GameNotRunningError as e:
            logger.warning(e)
            self.config.task_call('Restart')
            return False
        except (GameStuckError, GameTooManyClickError) as e:
            logger.error(e)
            self.save_error_log()
            logger.warning(f'Game stuck, {self.device.package} will be restarted in 10 seconds')
            logger.warning('If you are playing by hand, please stop Alas')
            self.config.task_call('Restart')
            self.device.sleep(10)
            return False
        except GameBugError as e:
            logger.warning(e)
            self.save_error_log()
            logger.warning('An error has occurred in Azur Lane game client, Alas is unable to handle')
            logger.warning(f'Restarting {self.device.package} to fix it')
            self.config.task_call('Restart')
            self.device.sleep(10)
            return False
        except GamePageUnknownError:
            logger.info('Game server may be under maintenance or network may be broken, check server status now')
            self.checker.check_now()
            if self.checker.is_available():
                logger.critical('Game page unknown')
                self.save_error_log()
                handle_notify(
                    self.config.Error_OnePushConfig,
                    title=f"Alas <{self.config_name}> crashed",
                    content=f"<{self.config_name}> GamePageUnknownError",
                )
                sys.exit(1)
            else:
                self.checker.wait_until_available()
                return False
        except ScriptError as e:
            logger.exception(e)
            logger.critical('This is likely to be a mistake of developers, but sometimes just random issues')
            handle_notify(
                self.config.Error_OnePushConfig,
                title=f"Alas <{self.config_name}> crashed",
                content=f"<{self.config_name}> ScriptError",
            )
            sys.exit(1)
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            handle_notify(
                self.config.Error_OnePushConfig,
                title=f"Alas <{self.config_name}> crashed",
                content=f"<{self.config_name}> RequestHumanTakeover",
            )
            sys.exit(1)
        except Exception as e:
            logger.exception(e)
            self.save_error_log()
            handle_notify(
                self.config.Error_OnePushConfig,
                title=f"Alas <{self.config_name}> crashed",
                content=f"<{self.config_name}> Exception occured",
            )
            sys.exit(1)

    def save_error_log(self):
        """
        Save last 60 screenshots in ./log/error/<timestamp>
        Save logs to ./log/error/<timestamp>/log.txt
        """
        from module.base.utils import save_image
        from module.handler.sensitive_info import (handle_sensitive_image,
                                                   handle_sensitive_logs)
        if self.config.Error_SaveError:
            if not os.path.exists('./log/error'):
                os.mkdir('./log/error')
            folder = f'./log/error/{int(time.time() * 1000)}'
            logger.warning(f'Saving error: {folder}')
            os.mkdir(folder)
            for data in self.device.screenshot_deque:
                image_time = datetime.strftime(data['time'], '%Y-%m-%d_%H-%M-%S-%f')
                image = handle_sensitive_image(data['image'])
                save_image(image, f'{folder}/{image_time}.png')
            with open(logger.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                start = 0
                for index, line in enumerate(lines):
                    line = line.strip(' \r\t\n')
                    if re.match('^═{15,}$', line):
                        start = index
                lines = lines[start - 2:]
                lines = handle_sensitive_logs(lines)
            with open(f'{folder}/log.txt', 'w', encoding='utf-8') as f:
                f.writelines(lines)

    def restart(self):
        from module.handler.login import LoginHandler
        LoginHandler(self.config, device=self.device).app_restart()

    def start(self):
        from module.handler.login import LoginHandler
        LoginHandler(self.config, device=self.device).app_start()

    def goto_main(self):
        from module.handler.login import LoginHandler
        from module.ui.ui import UI
        if self.device.app_is_running():
            logger.info('App is already running, goto main page')
            UI(self.config, device=self.device).ui_goto_main()
        else:
            logger.info('App is not running, start app and goto main page')
            LoginHandler(self.config, device=self.device).app_start()
            UI(self.config, device=self.device).ui_goto_main()

    def research(self):
        self.ui.ui_ensure(page_research)
        tools = self.state_machine.get_available_tools()
        for tool in tools:
            if tool.name == "research.run":
                tool.execute()
                break

    def commission(self):
        self.ui.ui_ensure(page_commission)
        tools = self.state_machine.get_available_tools()
        for tool in tools:
            if tool.name == "commission.run":
                tool.execute()
                break

    def tactical(self):
        from module.tactical.tactical_class import RewardTacticalClass
        RewardTacticalClass(config=self.config, device=self.device).run()

    def dorm(self):
        if not self.config.Dorm_Feed and not self.config.Dorm_Collect and not self.config.BuyFurniture_Enable:
            self.config.Scheduler_Enable = False
            self.config.task_stop()

        self.ui.ui_ensure(page_dormmenu)
        self.ui.handle_info_bar()

        collect = self.config.Dorm_Collect
        if not self.ui.appear(DORM_RED_DOT, offset=(30, 30)):
            logger.info('Nothing to collect. Dorm collecting skipped.')
            collect = False

        if not self.config.Dorm_Feed and not collect and not self.config.BuyFurniture_Enable:
            return

        self.ui.ui_goto(page_dorm, skip_first_screenshot=True)

        # Get tools
        tools = self.state_machine.get_available_tools()

        # Execute tools based on config
        if self.config.Dorm_Feed:
            logger.hr('Dorm feed', level=1)
            for tool in tools:
                if tool.name == "dorm.feed_ships":
                    tool.execute()
                    break

        if collect:
            logger.hr('Dorm collect', level=1)
            for tool in tools:
                if tool.name == "dorm.collect_rewards":
                    tool.execute()
                    break

        if self.config.BuyFurniture_Enable:
            logger.hr('Dorm buy furniture', level=1)
            for tool in tools:
                if tool.name == "dorm.buy_furniture":
                    tool.execute(buy_option=self.config.BuyFurniture_BuyOption)
                    break

        # Scheduler
        ships = 0
        for tool in tools:
            if tool.name == "dorm.get_ship_count":
                ships = tool.execute()
                break
        delay = self.cal_dorm_delay(ships)
        logger.info(f'Ships in dorm: {ships}, task to delay: {delay}')
        self.config.task_delay(minute=delay)

    def meowfficer(self):
        from module.meowfficer.meowfficer import RewardMeowfficer
        RewardMeowfficer(config=self.config, device=self.device).run()

    def guild(self):
        self.ui.ui_ensure(page_guild)
        tools = self.state_machine.get_available_tools()
        for tool in tools:
            if tool.name == "guild.collect_lobby_rewards":
                tool.execute()
                break

    def reward(self):
        from module.reward.reward import Reward
        Reward(config=self.config, device=self.device).run()

    def awaken(self):
        from module.awaken.awaken import Awaken
        Awaken(config=self.config, device=self.device).run()

    def shop_frequent(self):
        self.ui.ui_ensure(page_shop)
        tools = self.state_machine.get_available_tools()
        for tool in tools:
            if tool.name == "shop.run":
                tool.execute()
                break
        self.config.task_delay(server_update=True)

    def shop_once(self):
        from module.shop.shop_reward import RewardShop
        RewardShop(config=self.config, device=self.device).run_once()

    def shipyard(self):
        from module.shipyard.shipyard_reward import RewardShipyard
        RewardShipyard(config=self.config, device=self.device).run()

    def gacha(self):
        from module.gacha.gacha_reward import RewardGacha
        RewardGacha(config=self.config, device=self.device).run()

    def mail(self):
        self.ui.ui_ensure(page_main)
        tools = self.state_machine.get_available_tools()
        for tool in tools:
            if tool.name == "main.collect_mail":
                tool.execute()
                break

    def freebies(self):
        from module.freebies.freebies import Freebies
        Freebies(config=self.config, device=self.device).run()

    def minigame(self):
        from module.minigame.minigame import Minigame
        Minigame(config=self.config, device=self.device).run()

    def private_quarters(self):
        from module.private_quarters.private_quarters import PrivateQuarters
        PrivateQuarters(config=self.config, device=self.device).run()

    def daily(self):
        from module.daily.daily import Daily
        Daily(config=self.config, device=self.device).run()

    def hard(self):
        from module.hard.hard import CampaignHard
        CampaignHard(config=self.config, device=self.device).run()

    def exercise(self):
        from module.exercise.exercise import Exercise
        Exercise(config=self.config, device=self.device).run()

    def sos(self):
        from module.sos.sos import CampaignSos
        CampaignSos(config=self.config, device=self.device).run()

    def war_archives(self):
        from module.war_archives.war_archives import CampaignWarArchives
        CampaignWarArchives(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def raid_daily(self):
        from module.raid.daily import RaidDaily
        RaidDaily(config=self.config, device=self.device).run()

    def event_a(self):
        from module.event.campaign_abcd import CampaignABCD
        CampaignABCD(config=self.config, device=self.device).run()

    def event_b(self):
        from module.event.campaign_abcd import CampaignABCD
        CampaignABCD(config=self.config, device=self.device).run()

    def event_c(self):
        from module.event.campaign_abcd import CampaignABCD
        CampaignABCD(config=self.config, device=self.device).run()

    def event_d(self):
        from module.event.campaign_abcd import CampaignABCD
        CampaignABCD(config=self.config, device=self.device).run()

    def event_sp(self):
        from module.event.campaign_sp import CampaignSP
        CampaignSP(config=self.config, device=self.device).run()

    def maritime_escort(self):
        from module.event.maritime_escort import MaritimeEscort
        MaritimeEscort(config=self.config, device=self.device).run()

    def opsi_ash_assist(self):
        from module.os_ash.meta import AshBeaconAssist
        AshBeaconAssist(config=self.config, device=self.device).run()

    def opsi_ash_beacon(self):
        from module.os_ash.meta import OpsiAshBeacon
        OpsiAshBeacon(config=self.config, device=self.device).run()

    def opsi_explore(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_explore()

    def opsi_shop(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_shop()

    def opsi_voucher(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_voucher()

    def opsi_daily(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_daily()

    def opsi_obscure(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_obscure()

    def opsi_month_boss(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_month_boss()

    def opsi_abyssal(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_abyssal()

    def opsi_archive(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_archive()

    def opsi_stronghold(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_stronghold()

    def opsi_meowfficer_farming(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_meowfficer_farming()

    def opsi_hazard1_leveling(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_hazard1_leveling()

    def opsi_cross_month(self):
        from module.campaign.os_run import OSCampaignRun
        OSCampaignRun(config=self.config, device=self.device).opsi_cross_month()

    def main(self):
        from module.campaign.run import CampaignRun
        CampaignRun(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def main2(self):
        from module.campaign.run import CampaignRun
        CampaignRun(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def main3(self):
        from module.campaign.run import CampaignRun
        CampaignRun(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def event(self):
        from module.campaign.run import CampaignRun
        CampaignRun(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def event2(self):
        from module.campaign.run import CampaignRun
        CampaignRun(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def raid(self):
        from module.raid.run import RaidRun
        RaidRun(config=self.config, device=self.device).run()

    def hospital(self):
        from module.event_hospital.hospital import Hospital
        Hospital(config=self.config, device=self.device).run()

    def coalition(self):
        from module.coalition.coalition import Coalition
        Coalition(config=self.config, device=self.device).run()

    def coalition_sp(self):
        from module.coalition.coalition_sp import CoalitionSP
        CoalitionSP(config=self.config, device=self.device).run()

    def c72_mystery_farming(self):
        from module.campaign.run import CampaignRun
        CampaignRun(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def c122_medium_leveling(self):
        from module.campaign.run import CampaignRun
        CampaignRun(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def c124_large_leveling(self):
        from module.campaign.run import CampaignRun
        CampaignRun(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def gems_farming(self):
        from module.campaign.gems_farming import GemsFarming
        GemsFarming(config=self.config, device=self.device).run(
            name=self.config.Campaign_Name, folder=self.config.Campaign_Event, mode=self.config.Campaign_Mode)

    def daemon(self):
        from module.daemon.daemon import AzurLaneDaemon
        AzurLaneDaemon(config=self.config, device=self.device, task="Daemon").run()

    def opsi_daemon(self):
        from module.daemon.os_daemon import AzurLaneDaemon
        AzurLaneDaemon(config=self.config, device=self.device, task="OpsiDaemon").run()

    def event_story(self):
        from module.eventstory.eventstory import EventStory
        EventStory(config=self.config, device=self.device, task="EventStory").run()

    def azur_lane_uncensored(self):
        from module.daemon.uncensored import AzurLaneUncensored
        AzurLaneUncensored(config=self.config, device=self.device, task="AzurLaneUncensored").run()

    def benchmark(self):
        from module.daemon.benchmark import run_benchmark
        run_benchmark(config=self.config)

    def game_manager(self):
        from module.daemon.game_manager import GameManager
        GameManager(config=self.config, device=self.device, task="GameManager").run()

    def wait_until(self, future):
        """
        Wait until a specific time.

        Args:
            future (datetime):

        Returns:
            bool: True if wait finished, False if config changed.
        """
        future = future + timedelta(seconds=1)
        self.config.start_watching()
        while 1:
            if datetime.now() > future:
                return True
            if self.stop_event is not None:
                if self.stop_event.is_set():
                    logger.info("Update event detected")
                    logger.info(f"[{self.config_name}] exited. Reason: Update")
                    sys.exit(0)

            time.sleep(5)

            if self.config.should_reload():
                return False

    def get_next_task(self):
        """
        Returns:
            str: Name of the next task.
        """
        while 1:
            task = self.config.get_next()
            self.config.task = task
            self.config.bind(task)

            from module.base.resource import release_resources
            if self.config.task.command != 'Alas':
                release_resources(next_task=task.command)

            if task.next_run > datetime.now():
                logger.info(f'Wait until {task.next_run} for task `{task.command}`')
                self.is_first_task = False
                method = self.config.Optimization_WhenTaskQueueEmpty
                if method == 'close_game':
                    logger.info('Close game during wait')
                    self.device.app_stop()
                    release_resources()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
                    if task.command != 'Restart':
                        self.config.task_call('Restart')
                        del_cached_property(self, 'config')
                        continue
                elif method == 'goto_main':
                    logger.info('Goto main page during wait')
                    self.run('goto_main')
                    release_resources()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
                elif method == 'stay_there':
                    logger.info('Stay there during wait')
                    release_resources()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
                else:
                    logger.warning(f'Invalid Optimization_WhenTaskQueueEmpty: {method}, fallback to stay_there')
                    release_resources()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
            break

        AzurLaneConfig.is_hoarding_task = False
        return task.command

    def loop(self):
        logger.set_file_logger(self.config_name)
        logger.info(f'Start scheduler loop: {self.config_name}')

        while 1:
            # Check update event from GUI
            if self.stop_event is not None:
                if self.stop_event.is_set():
                    logger.info("Update event detected")
                    logger.info(f"Alas [{self.config_name}] exited.")
                    break
            # Check game server maintenance
            self.checker.wait_until_available()
            if self.checker.is_recovered():
                # There is an accidental bug hard to reproduce
                # Sometimes, config won't be updated due to blocking
                # even though it has been changed
                # So update it once recovered
                del_cached_property(self, 'config')
                logger.info('Server or network is recovered. Restart game client')
                self.config.task_call('Restart')
            # Get task
            task = self.get_next_task()
            # Init device and change server
            _ = self.device
            self.device.config = self.config
            # Skip first restart
            if self.is_first_task and task == 'Restart':
                logger.info('Skip task `Restart` at scheduler start')
                self.config.task_delay(server_update=True)
                del_cached_property(self, 'config')
                continue

            # Run
            logger.info(f'Scheduler: Start task `{task}`')
            self.device.stuck_record_clear()
            self.device.click_record_clear()
            logger.hr(task, level=0)
            success = self.run(inflection.underscore(task))
            logger.info(f'Scheduler: End task `{task}`')
            self.is_first_task = False

            # Check failures
            failed = deep_get(self.failure_record, keys=task, default=0)
            failed = 0 if success else failed + 1
            deep_set(self.failure_record, keys=task, value=failed)
            if failed >= 3:
                logger.critical(f"Task `{task}` failed 3 or more times.")
                logger.critical("Possible reason #1: You haven't used it correctly. "
                                "Please read the help text of the options.")
                logger.critical("Possible reason #2: There is a problem with this task. "
                                "Please contact developers or try to fix it yourself.")
                logger.critical('Request human takeover')
                handle_notify(
                    self.config.Error_OnePushConfig,
                    title=f"Alas <{self.config_name}> crashed",
                    content=f"<{self.config_name}> RequestHumanTakeover\nTask `{task}` failed 3 or more times.",
                )
                sys.exit(1)

            if success:
                del_cached_property(self, 'config')
                continue
            elif self.config.Error_HandleError:
                # self.config.task_delay(success=False)
                del_cached_property(self, 'config')
                self.checker.check_now()
                continue
            else:
                break


def _json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, default=str)


def cli_main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json

    from module.state_machine import StateMachine
    from module.ui.page import Page

    parser = argparse.ArgumentParser(prog="alas")
    parser.add_argument("--config", default="alas")
    subparsers = parser.add_subparsers(dest="command")

    tools_parser = subparsers.add_parser("tools")
    tools_sub = tools_parser.add_subparsers(dest="tools_cmd")

    tools_list = tools_sub.add_parser("list")
    tools_list.add_argument("--offline", action="store_true")

    tools_call = tools_sub.add_parser("call")
    tools_call.add_argument("name")
    tools_call.add_argument("--json", dest="json_args", default=None)

    page_parser = subparsers.add_parser("page")
    page_sub = page_parser.add_subparsers(dest="page_cmd")

    page_sub.add_parser("current")
    page_goto = page_sub.add_parser("goto")
    page_goto.add_argument("page")

    adb_parser = subparsers.add_parser("adb")
    adb_sub = adb_parser.add_subparsers(dest="adb_cmd")

    adb_screenshot = adb_sub.add_parser("screenshot")
    adb_screenshot.add_argument("--out", required=True)

    adb_tap = adb_sub.add_parser("tap")
    adb_tap.add_argument("x", type=int)
    adb_tap.add_argument("y", type=int)

    adb_swipe = adb_sub.add_parser("swipe")
    adb_swipe.add_argument("x1", type=int)
    adb_swipe.add_argument("y1", type=int)
    adb_swipe.add_argument("x2", type=int)
    adb_swipe.add_argument("y2", type=int)
    adb_swipe.add_argument("--duration-ms", type=int, default=None)

    args = parser.parse_args(argv)

    if args.command is None:
        AzurLaneAutoScript(config_name=args.config).loop()
        return 0

    if args.command == "tools":
        if args.tools_cmd == "list":
            if args.offline:
                sys.stdout.write(_json_dumps(StateMachine.tool_specs()) + "\n")
                return 0

            script = AzurLaneAutoScript(config_name=args.config)
            tools = [
                {"name": t.name, "description": t.description, "parameters": t.parameters}
                for t in script.state_machine.get_all_tools()
            ]
            sys.stdout.write(_json_dumps(tools) + "\n")
            return 0

        if args.tools_cmd == "call":
            tool_args: Dict[str, Any] = {}
            if args.json_args:
                tool_args = json.loads(args.json_args)
                if not isinstance(tool_args, dict):
                    raise TypeError("--json must be a JSON object")

            script = AzurLaneAutoScript(config_name=args.config)
            result = script.state_machine.call_tool(args.name, **tool_args)
            sys.stdout.write(_json_dumps(result) + "\n")
            return 0

        raise SystemExit("missing tools subcommand")

    if args.command == "page":
        script = AzurLaneAutoScript(config_name=args.config)
        if args.page_cmd == "current":
            page = script.state_machine.get_current_state()
            sys.stdout.write(str(page) + "\n")
            return 0
        if args.page_cmd == "goto":
            destination = Page.all_pages.get(args.page)
            if destination is None:
                raise KeyError(f"unknown page: {args.page}")
            script.state_machine.transition(destination)
            sys.stdout.write(f"navigated to {args.page}\n")
            return 0
        raise SystemExit("missing page subcommand")

    if args.command == "adb":
        script = AzurLaneAutoScript(config_name=args.config)
        if args.adb_cmd == "screenshot":
            image = script.device.screenshot()
            from PIL import Image

            if getattr(image, "shape", None) is not None and len(image.shape) == 3 and image.shape[2] == 3:
                img = Image.fromarray(image[:, :, ::-1])
            else:
                img = Image.fromarray(image)
            img.save(args.out)
            sys.stdout.write(f"saved {args.out}\n")
            return 0
        if args.adb_cmd == "tap":
            script.device.click_adb(args.x, args.y)
            sys.stdout.write(f"tapped {args.x},{args.y}\n")
            return 0
        if args.adb_cmd == "swipe":
            duration = 0.1 if args.duration_ms is None else (int(args.duration_ms) / 1000.0)
            script.device.swipe_adb((args.x1, args.y1), (args.x2, args.y2), duration=duration)
            sys.stdout.write(f"swiped {args.x1},{args.y1}->{args.x2},{args.y2}\n")
            return 0
        raise SystemExit("missing adb subcommand")

    raise SystemExit(f"unknown command: {args.command}")


def main() -> None:
    raise SystemExit(cli_main())


if __name__ == '__main__':
    raise SystemExit(cli_main())
