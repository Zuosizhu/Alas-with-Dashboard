import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Union

import numpy as np
from scipy.signal import find_peaks
from uiautomator2 import UiObject
from uiautomator2.exceptions import XPathElementNotFoundError
from uiautomator2.xpath import XPath, XPathSelector

import module.config.server as server
from module.base.timer import Timer
from module.base.utils import color_similarity_2d, crop, random_rectangle_point
from module.handler.assets import *
from module.logger import logger
from module.map.assets import *
from module.exception import GameStuckError
from module.ui.assets import *
from module.ui.page import page_campaign_menu
from module.ui.ui import UI


class LoginHandler(UI):
    LOGIN_MAX_TOTAL_SECONDS = 300
    LOGIN_MAX_NO_PROGRESS_SECONDS = 180
    LOGIN_TRACE_ROTATE_BYTES = 20 * 1024 * 1024
    _RUNTIME_ROOT = Path(__file__).resolve().parents[2]
    _trace_write_warned = False
    # Side-channel trace file: append-only JSONL so external parsers can
    # reconstruct login decisions without touching the normal logger stream.
    LOGIN_TRACE_FILE = str(_RUNTIME_ROOT / 'log' / 'login_trace.jsonl')

    def _trace_login_event(self, phase, detected=None, action=None, result=None, error=None, elapsed_ms=None):
        # Keep trace writes isolated from bot control flow; telemetry must
        # never alter runtime behavior.
        payload = {
            'ts': datetime.utcnow().isoformat(timespec='milliseconds') + 'Z',
            'config': getattr(self.config, 'config_name', 'unknown'),
            'phase': phase,
            'detected': detected,
            'action': action,
            'result': result,
            'error': error,
            'elapsed_ms': elapsed_ms,
        }
        try:
            folder = os.path.dirname(self.LOGIN_TRACE_FILE)
            if folder:
                os.makedirs(folder, exist_ok=True)
            if os.path.exists(self.LOGIN_TRACE_FILE) and os.path.getsize(self.LOGIN_TRACE_FILE) >= self.LOGIN_TRACE_ROTATE_BYTES:
                root, ext = os.path.splitext(self.LOGIN_TRACE_FILE)
                ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                rotated = f'{root}.{ts}{ext or ".jsonl"}'
                os.replace(self.LOGIN_TRACE_FILE, rotated)
            with open(self.LOGIN_TRACE_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(payload, ensure_ascii=True) + '\n')
        except Exception as e:
            # Trace logging must never break login flow.
            if not self._trace_write_warned:
                logger.warning(f'login_trace telemetry disabled: {type(e).__name__}: {e}')
                self._trace_write_warned = True

    def _handle_app_login(self):
        """
        Pages:
            in: Any page
            out: page_main

        Raises:
            GameStuckError:
            GameTooManyClickError:
            GameNotRunningError:
        """
        logger.hr('App login')

        confirm_timer = Timer(1.5, count=4).start()
        orientation_timer = Timer(5)
        login_success = False
        started_at = time.monotonic()
        last_progress_at = started_at
        self.device.stuck_record_clear()
        self.device.click_record_clear()
        self._trace_login_event(phase='start', result='begin', elapsed_ms=0)

        def elapsed_ms():
            return int((time.monotonic() - started_at) * 1000)

        def mark_progress(detected, action, result='progress'):
            nonlocal last_progress_at
            last_progress_at = time.monotonic()
            self._trace_login_event(
                phase='progress',
                detected=detected,
                action=action,
                result=result,
                elapsed_ms=elapsed_ms(),
            )

        while 1:
            now = time.monotonic()
            total_elapsed = now - started_at
            idle_elapsed = now - last_progress_at
            if total_elapsed > self.LOGIN_MAX_TOTAL_SECONDS:
                # Bound total login wall-clock runtime to avoid long blind loops.
                self._trace_login_event(
                    phase='guard',
                    action='abort',
                    result='timeout_total',
                    error=f'elapsed={total_elapsed:.1f}s',
                    elapsed_ms=elapsed_ms(),
                )
                raise GameStuckError(
                    f'Login timeout after {total_elapsed:.1f}s'
                )
            if idle_elapsed > self.LOGIN_MAX_NO_PROGRESS_SECONDS:
                # Bound no-progress window so we fail fast when UI is not changing.
                self._trace_login_event(
                    phase='guard',
                    action='abort',
                    result='timeout_no_progress',
                    error=f'idle={idle_elapsed:.1f}s',
                    elapsed_ms=elapsed_ms(),
                )
                raise GameStuckError(
                    f'Login no progress for {idle_elapsed:.1f}s'
                )

            # Watch device rotation
            if not login_success and orientation_timer.reached():
                # Screen may rotate after starting an app
                self.device.get_orientation()
                orientation_timer.reset()

            self.device.screenshot()

            # End
            if self.is_in_main():
                if confirm_timer.reached():
                    logger.info('Login to main confirm')
                    mark_progress(detected='page_main', action='confirm', result='success')
                    self._trace_login_event(
                        phase='end',
                        detected='page_main',
                        action='return',
                        result='success',
                        elapsed_ms=elapsed_ms(),
                    )
                    break
            else:
                confirm_timer.reset()

            # Login
            if self.match_template_color(LOGIN_CHECK, offset=(30, 30), interval=5):
                self.device.click(LOGIN_CHECK)
                mark_progress(detected='LOGIN_CHECK', action='click')
                if not login_success:
                    logger.info('Login success')
                    self._trace_login_event(
                        phase='login',
                        detected='LOGIN_CHECK',
                        action='login_success',
                        result='success',
                        elapsed_ms=elapsed_ms(),
                    )
                    login_success = True
            if self.appear(ANDROID_NO_RESPOND, offset=(30, 30), interval=5):
                logger.warning('Emulator no respond')
                self.device.click_record_add(ANDROID_NO_RESPOND)
                self.device.click_record_check()
                self.device.click(ANDROID_NO_RESPOND, control_check=False)
                mark_progress(detected='ANDROID_NO_RESPOND', action='click')
                continue
            if self.appear_then_click(LOGIN_ANNOUNCE, offset=(30, 30), interval=5):
                mark_progress(detected='LOGIN_ANNOUNCE', action='click')
                continue
            if self.appear_then_click(LOGIN_ANNOUNCE_2, offset=(30, 30), interval=5):
                mark_progress(detected='LOGIN_ANNOUNCE_2', action='click')
                continue
            if self.appear(EVENT_LIST_CHECK, offset=(30, 30), interval=5):
                self.device.click(BACK_ARROW)
                mark_progress(detected='EVENT_LIST_CHECK', action='click_back')
                continue
            # Updates and maintenance
            if self.appear_then_click(MAINTENANCE_ANNOUNCE, offset=(30, 30), interval=5):
                mark_progress(detected='MAINTENANCE_ANNOUNCE', action='click')
                continue
            if self.appear_then_click(LOGIN_GAME_UPDATE, offset=(30, 30), interval=5):
                mark_progress(detected='LOGIN_GAME_UPDATE', action='click')
                continue
            if server.server == 'cn' and not login_success:
                if self.handle_cn_user_agreement():
                    mark_progress(detected='CN_USER_AGREEMENT', action='handle')
                    continue
            # Player return
            if self.appear_then_click(LOGIN_RETURN_SIGN, offset=(30, 30), interval=5):
                mark_progress(detected='LOGIN_RETURN_SIGN', action='click')
                continue
            if self.appear_then_click(LOGIN_RETURN_INFO, offset=(30, 30), interval=5):
                mark_progress(detected='LOGIN_RETURN_INFO', action='click')
                continue
            # Popups
            if self.handle_popup_confirm('LOGIN'):
                mark_progress(detected='POPUP_CONFIRM', action='handle')
                continue
            if self.handle_urgent_commission():
                mark_progress(detected='URGENT_COMMISSION', action='handle')
                continue
            # Popups appear at page_main.
            # If popup handling succeeds, treat it as successful convergence for
            # login and exit immediately.
            if self.ui_page_main_popups(get_ship=login_success):
                mark_progress(detected='MAIN_POPUPS', action='handle', result='success')
                self._trace_login_event(
                    phase='end',
                    detected='MAIN_POPUPS',
                    action='return',
                    result='success',
                    elapsed_ms=elapsed_ms(),
                )
                return True
            # Always goto page_main
            if self.appear_then_click(GOTO_MAIN, offset=(30, 30), interval=5):
                mark_progress(detected='GOTO_MAIN', action='click')
                continue

        return True

    _user_agreement_timer = Timer(1, count=2)

    def handle_cn_user_agreement(self):
        if not self._user_agreement_timer.reached():
            return False

        confirm = self.image_color_button(
            area=(640, 360, 1280, 720), color=(78, 189, 234),
            color_threshold=245, encourage=25, name='AGREEMENT_CONFIRM')
        if confirm is None:
            return False
        scroll = self.image_color_button(
            area=(640, 0, 1280, 720), color=(182, 189, 202),
            color_threshold=245, encourage=5, name='AGREEMENT_SCROLL'
        )
        if scroll is not None:
            # User agreement
            p1 = random_rectangle_point(scroll.button)
            p2 = random_rectangle_point(scroll.move((0, 350)).button)
            self.device.swipe(p1, p2, name='AGREEMENT_SCROLL')
            self.device.click(confirm)
            self._user_agreement_timer.reset()
            return True
        else:
            # User login
            self.device.click(confirm)
            self._user_agreement_timer.reset()
            return True

    def handle_app_login(self):
        """
        Returns:
            bool: If login success

        Raises:
            GameStuckError:
            GameTooManyClickError:
            GameNotRunningError:
        """
        logger.info('handle_app_login')
        self.device.screenshot_interval_set(1.0)
        try:
            return self._handle_app_login()
        except Exception as e:
            # Preserve all existing logger behavior; we only add a side-channel
            # event so callers keep current failure semantics.
            self._trace_login_event(
                phase='error',
                action='raise',
                result='failed',
                error=type(e).__name__,
            )
            raise
        finally:
            self.device.screenshot_interval_set()

    def app_stop(self):
        logger.hr('App stop')
        self.device.app_stop()

    def app_start(self):
        logger.hr('App start')
        self.device.app_start()
        self.handle_app_login()
        # self.ensure_no_unfinished_campaign()

    def app_restart(self):
        logger.hr('App restart')
        self.device.app_stop()
        self.device.app_start()
        self.handle_app_login()
        # self.ensure_no_unfinished_campaign()
        self.config.task_delay(server_update=True)

    def ensure_no_unfinished_campaign(self, confirm_wait=3):
        """
        Pages:
            in: page_main
            out: page_main
        """

        def ensure_campaign_retreat():
            if self.appear_then_click(WITHDRAW, offset=(30, 30), interval=5):
                return True
            if self.handle_popup_confirm('WITHDRAW'):
                return True

        def in_campaign():
            return self.appear(CAMPAIGN_CHECK, offset=(30, 30)) \
                   or self.appear(CAMPAIGN_MENU_CHECK, offset=(30, 30)) \
                   or self.appear(EVENT_CHECK, offset=(30, 30)) \
                   or self.appear(SP_CHECK, offset=(30, 30))

        skip_first_screenshot = True
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            # End
            if in_campaign():
                break

            # Click
            if self.ui_main_appear_then_click(page_campaign_menu, interval=3):
                continue
            if ensure_campaign_retreat():
                continue

        self.ui_goto_main()

    def handle_user_agreement(self, xp, hierarchy):
        """
        For CN only.
        CN client is bugged. User Agreement and Privacy Policy may popup again even you have agreed with it.
        This method scrolls to the bottom and click AGREE.

        Returns:
            bool: If handled.
        """

        if server.server == 'cn':
            area_wait_results = self.get_for_any_ele([
                XPS('//*[@text="sdk协议"]', xp, hierarchy),
                XPS('//*[@content-desc="sdk协议"]', xp, hierarchy)])
            if area_wait_results is False:
                return False
            agree_wait_results = self.get_for_any_ele([
                XPS('//*[@text="同意"]', xp, hierarchy),
                XPS('//*[@content-desc="同意"]', xp, hierarchy)])
            start_padding_results = self.get_for_any_ele([
                XPS('//*[@text="隐私政策"]', xp, hierarchy), XPS('//*[@content-desc="隐私政策"]', xp, hierarchy),
                XPS('//*[@text="用户协议"]', xp, hierarchy), XPS('//*[@content-desc="用户协议"]', xp, hierarchy)])
            start_margin_results = self.get_for_any_ele([
                XPS('//*[@text="请滑动阅读协议内容"]', xp, hierarchy),
                XPS('//*[@content-desc="请滑动阅读协议内容"]', xp, hierarchy)])

            test_image_original = self.device.image
            image_handle_crop = crop(
                test_image_original, (start_padding_results[2], 0, start_margin_results[2], 720), copy=False)
            # Image.fromarray(image_handle_crop).show()
            sims = color_similarity_2d(image_handle_crop, color=(182, 189, 202))
            points = np.sum(sims >= 255)
            if points == 0:
                return False
            sims_height = np.mean(sims, axis=1)
            # pyplot.plot(sims_height, color='r')
            # pyplot.show()
            peaks, __ = find_peaks(sims_height, height=225)
            if len(peaks) == 2:
                peaks = (peaks[0] + peaks[1]) / 2
            start_pos = [(start_padding_results[2] + start_margin_results[2]) / 2, float(peaks)]
            end_pos = [(start_padding_results[2] + start_margin_results[2]) / 2, area_wait_results[3]]
            logger.info("user agreement position find result: " + ', '.join('%.2f' % _ for _ in start_pos))
            logger.info("user agreement area expect:          " + 'x:963-973, y:259-279')

            self.device.drag(start_pos, end_pos, segments=2, shake=(0, 25), point_random=(0, 0, 0, 0),
                             shake_random=(0, -5, 0, 5))
            AGREE = Button(area=agree_wait_results, color=(), button=agree_wait_results, name='AGREE')
            self.device.click(AGREE)
            return True

    def handle_user_login(self, xp, hierarchy) -> bool:
        login_wait_results = self.get_for_any_ele([
            XPS('//*[@text="登录"]', xp, hierarchy),
            XPS('//*[@content-desc="登录"]', xp, hierarchy)])
        if login_wait_results is False:
            return False
        else:
            USER_LOGIN_BTN = Button(area=login_wait_results, color=(), button=login_wait_results, name='USER_LOGIN_BTN')
            self.device.click(USER_LOGIN_BTN)
            return True

    @staticmethod
    def get_for_any_ele(list_u2_path: list) -> Union[bool, tuple]:
        """
        Args:
            list_u2_path (list): [UiObject or XPathSelector]  In this case, len(list_u2_path) >= 1
        Returns:
            bool: False if wait failed
            tuple: (bounds): if wait success
        """
        for path in list_u2_path:
            try:
                if isinstance(path, UiObject):
                    if path.exists():
                        return path.bounds()
                    elif not path.exists():
                        continue
                elif isinstance(path, XPathSelector):
                    if path.exists:
                        return path.bounds
                    elif not path.exists:
                        continue
            except XPathElementNotFoundError:
                continue
        return False

    def get_cn_xp_hierarchy(self) -> tuple:
        d = self.device.u2
        xp = XPath(d)
        hierarchy = d.dump_hierarchy()
        return xp, hierarchy


class XPS(XPathSelector):
    def __init__(self, xpath, parent, source):
        super().__init__(parent, xpath, source)
