
import sys
import contextlib
import io
from pathlib import Path


def main():
    # Add alas_wrapped to path so ALAS imports work
    alas_dir = (Path(__file__).resolve().parents[1] / "alas_wrapped").resolve()
    sys.path.insert(0, str(alas_dir))

    from dev_tools.record_scenario import ScenarioRecorder, DevicePatchSession
    from alas_mcp_server import ALASContext
    from module.ui.page import Page

    print('=== LLM ALAS Wander & Capture ===')
    _buf = io.StringIO()
    with contextlib.redirect_stdout(_buf):
        ctx = ALASContext('alas')

    print('[1] Context initialized. Registering capture session...')
    base_dir = (Path(__file__).resolve().parent / "wander_out").resolve()
    recorder = ScenarioRecorder('llm_wander', base_dir=base_dir)

    with DevicePatchSession(device=ctx.script.device, recorder=recorder):
        print('[2] Executing Reward Collection Workflow...')
        ctx.script.reward()

        print('[3] Navigating to dorm...')
        dest = Page.all_pages.get('page_dorm')
        with contextlib.redirect_stdout(_buf):
            ctx._state_machine.transition(dest)
            state = ctx._state_machine.get_current_state()
            print(f'Arrived at: {state}')
            ctx.script.device.screenshot() # force an extra capture
            ctx.script.device.click((100, 100))  # upper-left safe region (no UI element on 1280×720)

        print('[4] Back to main...')
        dest = Page.all_pages.get('page_main')
        with contextlib.redirect_stdout(_buf):
            ctx._state_machine.transition(dest)
            state = ctx._state_machine.get_current_state()
            print(f'Arrived at: {state}')
            ctx.script.device.screenshot()

    print(f'Recorded {recorder._event_index} events and {recorder._frame_index} frames.')
    print('Saved to: ' + str(recorder.fixture_dir))
    print('=== Done ===')


if __name__ == "__main__":
    main()
