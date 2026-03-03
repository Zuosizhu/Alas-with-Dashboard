"""
LLM-as-Scheduler pilot loop.

Replaces the ALAS scheduler with direct Python-driven task execution.
Runs all available tools on cooldown, recovers to page_main on any error.

Usage:
    cd agent_orchestrator
    uv run python llm_pilot.py [--config alas]           # start pilot loop
    uv run python llm_pilot.py --kill                     # kill running instance
    uv run python llm_pilot.py --restart [--config alas]  # kill + start fresh
"""
from __future__ import annotations

import argparse
import multiprocessing
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

PID_FILE = Path(__file__).parent / "llm_pilot.pid"
LOG_FILE = Path(__file__).parent / "llm_pilot.log"

sys.path.insert(0, str(Path(__file__).parent.parent / "alas_wrapped"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="alas")
    p.add_argument("--kill", action="store_true", help="Kill running pilot instance and exit")
    p.add_argument("--restart", action="store_true", help="Kill running pilot, then start fresh")
    p.add_argument("--skip-mail", action="store_true", help="Skip main.collect_mail")
    p.add_argument(
        "--skip-tool",
        action="append",
        default=[],
        help="Skip tool by exact name (repeatable), e.g. --skip-tool commission.run",
    )
    p.add_argument(
        "--startup-state-timeout-s",
        type=float,
        default=20.0,
        help="Grace period before treating unknown startup state as recovery-worthy",
    )
    return p.parse_args()


def setup_log():
    fh = open(LOG_FILE, "a", encoding="utf-8")

    def log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}][pid={os.getpid()}] {msg}"
        print(line, flush=True)
        fh.write(line + "\n")
        fh.flush()

    return log


# ---------------------------------------------------------------------------
# Process lifecycle: find, kill, guard
# ---------------------------------------------------------------------------

def _is_pilot_process(proc_name: str, cmdline: list[str]) -> bool:
    """Return True only for python/uv processes directly launching llm_pilot.py."""
    name = (proc_name or "").lower()
    if name not in {"python", "python.exe", "uv", "uv.exe"}:
        return False
    for arg in cmdline:
        a = str(arg).replace("\\", "/").lower()
        if a.endswith("/llm_pilot.py") or a == "llm_pilot.py":
            return True
    return False


def _is_pilot_pid(pid: int) -> bool:
    """Return True if pid belongs to llm_pilot.py."""
    try:
        import psutil
        proc = psutil.Process(pid)
        cmdline = proc.cmdline() or []
        return proc.is_running() and _is_pilot_process(proc.name(), cmdline)
    except Exception:
        return False


def _list_running_pilots() -> list[int]:
    """Return all running llm_pilot.py PIDs (excluding current process)."""
    pids: set[int] = set()
    current_pid = os.getpid()
    try:
        import psutil
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            pid = int(proc.info["pid"])
            if pid == current_pid:
                continue
            cmdline = proc.info.get("cmdline") or []
            name = str(proc.info.get("name") or "")
            if _is_pilot_process(name, cmdline):
                pids.add(pid)
    except Exception:
        pass

    # Also trust pid file if it points to a live pilot process.
    if PID_FILE.exists():
        try:
            file_pid = int(PID_FILE.read_text().strip())
            if file_pid != current_pid and _is_pilot_pid(file_pid):
                pids.add(file_pid)
        except Exception:
            pass

    return sorted(pids)


def _find_running_pilot() -> int | None:
    """Return running pilot PID from pid file, or None."""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        return pid if _is_pilot_pid(pid) else None
    except Exception:
        return None


def kill_pilot() -> bool:
    """Kill all running pilot instances. Returns True if any were killed."""
    pids = _list_running_pilots()
    if not pids:
        print("[llm_pilot] No running instance found.")
        PID_FILE.unlink(missing_ok=True)
        return False

    print(f"[llm_pilot] Killing {len(pids)} instance(s): {pids}")
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            # Wait up to 5s for graceful shutdown
            import psutil
            psutil.Process(pid).wait(timeout=5)
        except Exception:
            try:
                os.kill(pid, 9)  # force kill
            except OSError:
                pass

    PID_FILE.unlink(missing_ok=True)
    print("[llm_pilot] Killed.")
    return True


def _write_pid():
    """Write current process PID to the pid file."""
    PID_FILE.write_text(str(os.getpid()))


def _guard_single_instance():
    """Exit if another pilot is already running."""
    pid = _find_running_pilot()
    if pid is not None:
        print(f"[llm_pilot] Another instance is already running (PID {pid}). Exiting.")
        print("[llm_pilot] Use --kill or --restart to replace it.")
        sys.exit(0)


def recover_to_main(ctx, log) -> bool:
    log("... recovering to page_main")
    try:
        from module.ui.page import Page
        dest = Page.all_pages.get("page_main")
        ctx._state_machine.transition(dest)
        state = ctx._state_machine.get_current_state()
        log(f"... recovered, now at {state}")
        return True
    except Exception as e:
        log(f"... recovery failed: {type(e).__name__}: {e}")
        return False


def get_current_state_with_grace(ctx, timeout_s: float, poll_interval_s: float = 1.0) -> str:
    """Poll current state for a short grace window to absorb screen-transition lag."""
    deadline = time.time() + max(timeout_s, 0.0)
    last_error: Exception | None = None
    while True:
        try:
            return str(ctx._state_machine.get_current_state())
        except Exception as e:
            last_error = e
            if time.time() >= deadline:
                break
            time.sleep(max(poll_interval_s, 0.1))
    if last_error is not None:
        raise last_error
    raise RuntimeError("could not determine current state")


def run_tool(ctx, tool_name: str, log) -> bool:
    tool_map = {t.name: t for t in ctx._state_machine.get_all_tools()}
    if tool_name not in tool_map:
        log(f"SKIP {tool_name} - not in tool registry")
        return False
    tool = tool_map[tool_name]
    try:
        log(f">>> START {tool_name}")
        tool.execute()
        log(f"<<< DONE  {tool_name}")
        return True
    except Exception as e:
        if type(e).__name__ == "GamePageUnknownError":
            log(f"... transient unknown page during {tool_name}; retrying once after 3s")
            time.sleep(3)
            try:
                tool.execute()
                log(f"<<< DONE  {tool_name} (after retry)")
                return True
            except Exception as retry_error:
                log(f"!!! ERROR {tool_name} (retry): {type(retry_error).__name__}: {retry_error}")
                log(traceback.format_exc()[-600:])
                return False
        log(f"!!! ERROR {tool_name}: {type(e).__name__}: {e}")
        log(traceback.format_exc()[-600:])
        return False


# (tool_name, cooldown_minutes)
# cooldown=0 means "always run when due" (first run always due)
TASKS = [
    ("main.collect_mail",           60),
    ("workflow.daily_base_sweep",    0),   # first run always runs; cooldown set after
    ("commission.run",             180),
    # research.run requires cnocr (CN OCR library) which is not available in
    # the agent_orchestrator Python 3.14 venv. Disabled until resolved.
    # ("research.run",               60),
    ("dorm.collect_rewards",        60),
    # dorm.feed_ships requires cnocr (CN OCR library) which is not available
    # in the agent_orchestrator Python 3.14 venv. Disabled until resolved.
    # ("dorm.feed_ships",           120),
    # guild.collect_lobby_rewards consistently fails with GameStuckError.
    # The guild lobby buttons (GUILD_REPORT_CLAIM etc.) don't match the EN
    # game UI after clicking, causing the stuck_record_check to fire after 1 min.
    # Disabled until guild module button assets are verified against EN client.
    # ("guild.collect_lobby_rewards", 360),
    # shop.run requires cnocr (CN OCR library) which is not available in the
    # agent_orchestrator Python 3.14 venv. Disabled until dependency resolved.
    # ("shop.run",                 180),
]
# After first run, daily_base_sweep goes on a 6-hour cooldown
AFTER_FIRST_RUN_COOLDOWN = {"workflow.daily_base_sweep": 360}


def main():
    args = parse_args()

    # Handle --kill
    if args.kill:
        kill_pilot()
        sys.exit(0)

    # Handle --restart
    if args.restart:
        kill_pilot()
        time.sleep(2)  # let the old process fully die

    log = setup_log()

    # Single-instance guard
    _guard_single_instance()
    _write_pid()

    try:
        _run_loop(args, log)
    finally:
        PID_FILE.unlink(missing_ok=True)


def _run_loop(args, log):

    log("=" * 60)
    log("LLM PILOT START")
    log("=" * 60)

    from alas_mcp_server import ALASContext
    ctx = ALASContext(config_name=args.config)

    # Startup recovery: give transient page-detection lag a grace window first.
    try:
        state = get_current_state_with_grace(ctx, timeout_s=args.startup_state_timeout_s)
        log(f"Connected. Initial state: {state}")
    except Exception as e:
        log(
            f"Startup: state unresolved after {int(args.startup_state_timeout_s)}s "
            f"({type(e).__name__}), attempting recovery..."
        )
        from module.ui.page import Page
        dest = Page.all_pages.get("page_main")
        try:
            ctx._state_machine.transition(dest)
            state = get_current_state_with_grace(ctx, timeout_s=10.0)
            log(f"Startup recovery: recovered to {state}")
        except Exception as e2:
            log(f"Startup recovery failed: {e2}")
            log("Cannot proceed without a known game state. Exiting.")
            sys.exit(1)

    available = [t.name for t in ctx._state_machine.get_all_tools()]
    log(f"Available tools: {available}")

    skip_tools = set(args.skip_tool or [])
    if args.skip_mail:
        skip_tools.add("main.collect_mail")
    active_tasks = [(name, cd) for name, cd in TASKS if name not in skip_tools]
    if skip_tools:
        log(f"Skipping tools: {sorted(skip_tools)}")
    if not active_tasks:
        log("No active tasks after skip filters. Exiting.")
        return

    last_run: dict[str, float] = {}
    effective_cooldown: dict[str, int] = {name: cd for name, cd in active_tasks}
    round_num = 0

    while True:
        round_num += 1
        now = time.time()
        ran_any = False

        for tool_name, _ in active_tasks:
            cooldown_min = effective_cooldown[tool_name]
            last = last_run.get(tool_name, 0)
            if now - last < cooldown_min * 60:
                continue  # not due yet

            ok = run_tool(ctx, tool_name, log)
            last_run[tool_name] = time.time()
            ran_any = True

            # Apply post-first-run cooldown if defined
            if tool_name in AFTER_FIRST_RUN_COOLDOWN:
                effective_cooldown[tool_name] = AFTER_FIRST_RUN_COOLDOWN[tool_name]

            if not ok:
                recover_to_main(ctx, log)

            time.sleep(5)   # pause between tasks

        if not ran_any:
            # Find soonest task
            candidates = [
                last_run.get(n, 0) + effective_cooldown[n] * 60
                for n, _ in active_tasks
                if effective_cooldown[n] > 0
            ]
            sleep_until = min(candidates) if candidates else now + 300
            sleep_secs = max(60, int(sleep_until - time.time()))
            wake_time = datetime.fromtimestamp(time.time() + sleep_secs).strftime("%H:%M:%S")
            log(f"[round {round_num}] All tasks on cooldown. Sleeping {sleep_secs//60}m until {wake_time}")
            time.sleep(sleep_secs)
        else:
            time.sleep(10)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
