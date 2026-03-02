import os
import re
import threading
import time
from datetime import datetime, timedelta

import inflection
from cached_property import cached_property
try:
    from adbutils.errors import AdbError
except ImportError:
    class AdbError(Exception):
        pass

from module.base.decorator import del_cached_property
from module.base.jsonl import append_jsonl
from module.config.config import AzurLaneConfig, TaskEnd
from module.config.deep import deep_get, deep_set
from module.exception import *
from module.logger import logger
from module.notify import handle_notify

# Command whitelist for security (frozenset for O(1) lookup)
_ALLOWED_COMMANDS = frozenset([
    'restart', 'start', 'goto_main', 'research', 'commission', 'tactical',
    'dorm', 'meowfficer', 'guild', 'reward', 'awaken', 'shop_frequent',
    'shop_once', 'shipyard', 'gacha', 'freebies', 'minigame', 'private_quarters',
    'daily', 'hard', 'exercise', 'sos', 'war_archives', 'raid_daily',
    'event_a', 'event_b', 'event_c', 'event_d', 'event_sp', 'maritime_escort',
    'opsi_ash_assist', 'opsi_ash_beacon', 'opsi_explore', 'opsi_shop',
    'opsi_voucher', 'opsi_daily', 'opsi_obscure', 'opsi_month_boss',
    'opsi_abyssal', 'opsi_archive', 'opsi_stronghold', 'opsi_meowfficer_farming',
    'opsi_hazard1_leveling', 'opsi_cross_month', 'main', 'main2', 'main3',
    'event', 'event2', 'raid', 'hospital', 'coalition', 'coalition_sp',
    'c72_mystery_farming', 'c122_medium_leveling', 'c124_large_leveling',
    'gems_farming', 'daemon', 'opsi_daemon', 'event_story',
    'azur_lane_uncensored', 'benchmark', 'game_manager'
])

_RUNTIME_ROOT = os.path.dirname(os.path.abspath(__file__))
_SCHEDULE_STATUS_FILE = os.path.join(_RUNTIME_ROOT, 'log', 'schedule_status.jsonl')
_JSONL_ROTATE_BYTES = 20 * 1024 * 1024


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
        # Used by sidecar schedule status logs for correlation.
        self.last_task = None
        # Count transport failures across consecutive run attempts:
        # first failure may be transient; repeated failures force restart path.
        self.transport_error_streak = 0
        # Prevents duplicate restart calls when one restart is already queued.
        self.restart_dedupe_seconds = 30

    @cached_property
    def config(self):
        try:
            config = AzurLaneConfig(config_name=self.config_name)
            return config
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            raise
        except Exception as e:
            logger.exception(e)
            raise RequestHumanTakeover(str(e)) from e

    @cached_property
    def device(self):
        try:
            from module.device.device import Device
            device = Device(config=self.config)
            return device
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            raise
        except Exception as e:
            logger.exception(e)
            raise RequestHumanTakeover(str(e)) from e

    @cached_property
    def checker(self):
        try:
            from module.server_checker import ServerChecker
            checker = ServerChecker(server=self.config.Emulator_ServerName)
            return checker
        except Exception as e:
            logger.exception(e)
            raise RequestHumanTakeover(str(e)) from e

    @cached_property
    def state_machine(self):
        try:
            from module.state_machine import StateMachine
            from module.ui.ui import UI
            ui = UI(config=self.config, device=self.device)
            return StateMachine(ui=ui)
        except Exception as e:
            logger.exception(e)
            raise RequestHumanTakeover(str(e)) from e

    def _write_schedule_status(self, next_task):
        # Emit scheduler intent and task queues to a separate stream so
        # external tooling can inspect current/next task order.
        pending = [f.command for f in getattr(self.config, 'pending_task', [])]
        waiting = [f.command for f in getattr(self.config, 'waiting_task', [])]
        payload = {
            'ts': datetime.utcnow().isoformat(timespec='milliseconds') + 'Z',
            'config': self.config_name,
            'current_task': self.last_task,
            'next_task': next_task,
            'pending': pending,
            'next_waiting': waiting[:10],
            'pending_count': len(pending),
            'waiting_count': len(waiting),
            'source': 'scheduler_loop',
        }
        append_jsonl(
            _SCHEDULE_STATUS_FILE,
            payload,
            rotate_bytes=_JSONL_ROTATE_BYTES,
            error_callback=lambda e: logger.warning(
                f'Failed to append JSONL `{_SCHEDULE_STATUS_FILE}`: {e}'
            ),
        )

    def _is_restart_pending_soon(self, within_seconds=None):
        # Treat an existing upcoming Restart task as already-reported work.
        within_seconds = self.restart_dedupe_seconds if within_seconds is None else within_seconds
        restart_next_run = deep_get(self.config.data, keys='Restart.Scheduler.NextRun', default=None)
        restart_enabled = bool(deep_get(self.config.data, keys='Restart.Scheduler.Enable', default=False))
        if not restart_enabled or not isinstance(restart_next_run, datetime):
            return False
        return restart_next_run <= datetime.now() + timedelta(seconds=max(int(within_seconds), 0))

    def _schedule_restart(self, reason, within_seconds=None):
        # Centralize all restart scheduling through one dedupe-aware path.
        if self._is_restart_pending_soon(within_seconds=within_seconds):
            logger.info(f'Task call: Restart (deduped, already pending) reason={reason}')
            return False
        logger.info(f'Task call: Restart (reason={reason})')
        self.config.task_call('Restart')
        return True

    def _recover_transport_once(self, reason):
        # Use a single reconnect-screenshot probe before declaring transport
        # failure terminal and letting restart logic run.
        logger.warning(f'Transport failure detected ({reason}), attempting adb_reconnect once')
        try:
            self.device.adb_reconnect()
            self.device.screenshot()
            logger.info('Transport recovery succeeded')
            return True
        except Exception as e:
            logger.warning(f'Transport recovery failed: {type(e).__name__}: {e}')
            return False

    def run(self, command, skip_first_screenshot=False):
        """
        Args:
            command (str): Task name to run.
            skip_first_screenshot (bool):
        """
        if command not in _ALLOWED_COMMANDS:
            logger.error(f'Command "{command}" is not in the whitelist.')
            return False

        try:
            if not skip_first_screenshot:
                self.device.screenshot()
            self.__getattribute__(command)()
            self.transport_error_streak = 0
            return True
        except TaskEnd:
            self.transport_error_streak = 0
            return True
        except GameNotRunningError as e:
            self.transport_error_streak = 0
            logger.warning(e)
            self._schedule_restart(reason='game_not_running')
            return False
        except (GameStuckError, GameTooManyClickError) as e:
            self.transport_error_streak = 0
            logger.error(e)
            self.save_error_log()
            logger.warning(f'Game stuck, {self.device.package} will be restarted in 10 seconds')
            logger.warning('If you are playing by hand, please stop Alas')
            self._schedule_restart(reason=f'ui_stuck:{type(e).__name__}')
            self.device.sleep(10)
            return False
        except (AdbError, GameTransportError) as e:
            self.transport_error_streak += 1
            logger.error(f'{type(e).__name__}: {e}')
            self.save_error_log()
            # One-shot recovery: avoid immediate restart churn on one-off ADB blips.
            if self.transport_error_streak == 1 and self._recover_transport_once(reason=f'{command}:{type(e).__name__}'):
                logger.warning('Transport recovered on first failure, skip immediate restart')
                self.device.sleep(2)
                return False
            logger.warning('Transport failure repeated or unrecoverable, schedule restart')
            self._schedule_restart(reason=f'transport_failure:{type(e).__name__}')
            self.device.sleep(10)
            return False
        except GameBugError as e:
            self.transport_error_streak = 0
            logger.warning(e)
            self.save_error_log()
            logger.warning('An error has occurred in Azur Lane game client, Alas is unable to handle')
            logger.warning(f'Restarting {self.device.package} to fix it')
            self._schedule_restart(reason='game_bug')
            self.device.sleep(10)
            return False
        except GamePageUnknownError:
            self.transport_error_streak = 0
            logger.info('Game server may be under maintenance or network may be broken, check server status now')
            self.checker.check_now()
            if self.checker.is_available():
                if self.config.Error_RestartOnUnknownPage:
                    logger.warning('Game page unknown, server is available. Attempting restart.')
                    self.save_error_log()
                    self._schedule_restart(reason='unknown_page')
                    self.device.sleep(10)
                    return False
                else:
                    logger.critical('Game page unknown')
                    self.save_error_log()
                    handle_notify(
                        self.config.Error_OnePushConfig,
                        title=f"Alas <{self.config_name}> crashed",
                        content=f"<{self.config_name}> GamePageUnknownError",
                    )
                    raise RequestHumanTakeover('GamePageUnknownError')
            else:
                logger.warning('Game server is under maintenance or network is broken, Alas will wait for it')
                self.checker.wait_until_available()
                return False
        except ScriptError as e:
            self.transport_error_streak = 0
            logger.exception(e)
            logger.critical('This is likely to be a mistake of developers, but sometimes just random issues')
            handle_notify(
                self.config.Error_OnePushConfig,
                title=f"Alas <{self.config_name}> crashed",
                content=f"<{self.config_name}> ScriptError",
            )
            raise RequestHumanTakeover(str(e)) from e
        except RequestHumanTakeover:
            self.transport_error_streak = 0
            logger.critical('Request human takeover')
            handle_notify(
                self.config.Error_OnePushConfig,
                title=f"Alas <{self.config_name}> crashed",
                content=f"<{self.config_name}> RequestHumanTakeover",
            )
            raise
        except Exception as e:
            self.transport_error_streak = 0
            logger.exception(e)
            self.save_error_log()
            handle_notify(
                self.config.Error_OnePushConfig,
                title=f"Alas <{self.config_name}> crashed",
                content=f"<{self.config_name}> Exception occured",
            )
            raise RequestHumanTakeover(str(e)) from e
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
        from module.research.research import RewardResearch
        RewardResearch(config=self.config, device=self.device).run()

    def commission(self):
        from module.commission.commission import RewardCommission
        RewardCommission(config=self.config, device=self.device).run()

    def tactical(self):
        from module.tactical.tactical_class import RewardTacticalClass
        RewardTacticalClass(config=self.config, device=self.device).run()

    def dorm(self):
        from module.dorm.dorm import RewardDorm
        RewardDorm(config=self.config, device=self.device).run()

    def meowfficer(self):
        from module.meowfficer.meowfficer import RewardMeowfficer
        RewardMeowfficer(config=self.config, device=self.device).run()

    def guild(self):
        from module.guild.guild_reward import RewardGuild
        RewardGuild(config=self.config, device=self.device).run()

    def reward(self):
        from module.reward.reward import Reward
        Reward(config=self.config, device=self.device).run()

    def awaken(self):
        from module.awaken.awaken import Awaken
        Awaken(config=self.config, device=self.device).run()

    def shop_frequent(self):
        from module.shop.shop_reward import RewardShop
        RewardShop(config=self.config, device=self.device).run_frequent()

    def shop_once(self):
        from module.shop.shop_reward import RewardShop
        RewardShop(config=self.config, device=self.device).run_once()

    def shipyard(self):
        from module.shipyard.shipyard_reward import RewardShipyard
        RewardShipyard(config=self.config, device=self.device).run()

    def gacha(self):
        from module.gacha.gacha_reward import RewardGacha
        RewardGacha(config=self.config, device=self.device).run()

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
                    return False

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
                        self._schedule_restart(reason='close_game_wait')
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
                self._schedule_restart(reason='server_recovered')
            # Get task
            task = self.get_next_task()
            self._write_schedule_status(next_task=task)
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
            self.last_task = task

            # Check failures
            failed = self.failure_record.get(task, 0)
            failed = 0 if success else failed + 1
            self.failure_record[task] = failed
            if failed >= 3:
                logger.critical(f"Task `{task}` failed 3 or more times.")
                logger.critical("Possible reason #1: You haven't used it correctly. "
                                "Please read the help text of the options.")
                logger.critical("Possible reason #2: There is a problem with this task. "
                                "Please contact developers or try to fix it yourself.")
                if self.config.Error_HandleError:
                    logger.warning(f"Auto recovery enabled, skip human takeover for task `{task}`")
                    logger.warning(f"Delay task `{task}` for 10 minutes and schedule `Restart`")
                    self.failure_record[task] = 0
                    self.config.task_delay(task=task, minute=10)
                    self._schedule_restart(reason=f'task_failed_3x:{task}')
                    if task == 'Restart':
                        logger.warning('Restart task failed repeatedly, wait 60 seconds before next scheduler cycle')
                        # Use time.sleep directly: device.sleep is only a thin
                        # wrapper today, but when Restart itself has failed the
                        # device/ADB connection may be in an unknown state.
                        time.sleep(60)
                    del_cached_property(self, 'config')
                    continue
                logger.critical('Request human takeover')
                handle_notify(
                    self.config.Error_OnePushConfig,
                    title=f"Alas <{self.config_name}> crashed",
                    content=f"<{self.config_name}> RequestHumanTakeover\nTask `{task}` failed 3 or more times.",
                )
                raise RequestHumanTakeover(f"Task `{task}` failed 3 or more times.")

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


if __name__ == '__main__':
    alas = AzurLaneAutoScript()
    alas.loop()
