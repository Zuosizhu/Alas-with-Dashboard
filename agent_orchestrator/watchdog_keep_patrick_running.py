"""
watchdog_keep_patrick_running.py

Monitors the ALAS PatrickCustom bot and relaunches gui.py if the bot has paused.

How it works:
  - The bot writes log lines continuously while running (every ~0.3-1.0 seconds
    during active tasks, plus periodic "Scheduler: Next run" lines while idle).
  - If no new log lines appear for longer than `stale_threshold_minutes`, the
    bot has paused, stopped, or been killed.
  - On detection, we kill all gui.py instances and relaunch gui.py --run PatrickCustom.
    This is equivalent to clicking "Start" in the web UI — on startup, gui.py
    automatically calls ProcessManager.restart_processes(instances=["PatrickCustom"]).

What it does NOT do:
  - It does not check whether the gui.py process is alive. gui.py being alive
    says nothing about whether the bot scheduler loop is running; when the user
    clicks Stop, gui.py stays alive but the bot worker subprocess is killed.
  - It does not attempt to directly call ProcessManager.start() — there is no
    external HTTP or socket API for this.
"""

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import psutil


def utc_now() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def write_log(event: str, log_path: Path, **data) -> None:
    actor = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
    payload = {"ts": utc_now(), "event": event, "actor": actor}
    payload.update(data)
    line = json.dumps(payload, ensure_ascii=True)
    print(line, flush=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def find_alas_log(alas_wrapped_dir: Path, config_name: str) -> Optional[Path]:
    """Find the most recent ALAS log file for this config (today's date first)."""
    log_dir = alas_wrapped_dir / "log"
    # ALAS logger uses only the first token before "_" in the config name.
    logger_name = config_name.split("_", 1)[0]
    today = dt.date.today().strftime("%Y-%m-%d")
    candidate = log_dir / f"{today}_{logger_name}.txt"
    if candidate.exists():
        return candidate
    # Fall back to most recent matching file (allow both logger token and full config name).
    matches = sorted(
        list(log_dir.glob(f"*_{logger_name}.txt")) + list(log_dir.glob(f"*_{config_name}.txt")),
        reverse=True,
    )
    return matches[0] if matches else None


def get_log_stale_seconds(log_path: Path) -> float:
    """Return number of seconds since the log file was last written to."""
    return time.time() - log_path.stat().st_mtime


def kill_gui_processes(alas_wrapped_dir: Path) -> List[int]:
    """Kill all ALAS gui.py processes running from this alas_wrapped directory."""
    killed = []
    target_dir = str(alas_wrapped_dir).replace("\\", "/").lower()
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if not cmdline:
                continue
            normalized_parts = [str(part).replace("\\", "/").lower() for part in cmdline]
            has_gui = any(part.endswith("/gui.py") or part == "gui.py" for part in normalized_parts)
            if not has_gui:
                continue

            joined = " ".join(normalized_parts)
            is_target = target_dir in joined
            if not is_target:
                try:
                    proc_cwd = str(Path(proc.cwd()).resolve()).replace("\\", "/").lower()
                    is_target = proc_cwd == target_dir
                except (psutil.NoSuchProcess, psutil.AccessDenied, FileNotFoundError):
                    is_target = False

            if is_target:
                proc.kill()
                killed.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed


def resolve_python_exe(alas_wrapped_dir: Path) -> str:
    candidates = [
        alas_wrapped_dir / ".venv" / "Scripts" / "python.exe",
        alas_wrapped_dir / "venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    for binary in ("python.exe", "python"):
        found = shutil.which(binary)
        if found:
            return found

    raise FileNotFoundError("No Python executable found for watchdog relaunch")


def start_gui(alas_wrapped_dir: Path, config_name: str) -> None:
    """Launch gui.py --run <config_name> as a detached background process."""
    python_exe = resolve_python_exe(alas_wrapped_dir)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    creationflags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0)
    )
    subprocess.Popen(
        [python_exe, "gui.py", "--run", config_name],
        cwd=str(alas_wrapped_dir),
        env=env,
        creationflags=creationflags,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Keep ALAS config running by monitoring log staleness"
    )
    parser.add_argument("--config", default="PatrickCustom", help="ALAS config name")
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=5,
        help="How often to check, in minutes (default: 5)",
    )
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=15,
        help=(
            "If no new log lines for this many minutes, consider the bot paused "
            "and relaunch (default: 15)"
        ),
    )
    parser.add_argument(
        "--alas-wrapped-dir",
        default=str((Path(__file__).resolve().parents[1] / "alas_wrapped")),
        help="Path to alas_wrapped directory",
    )
    args = parser.parse_args()

    alas_wrapped_dir = Path(args.alas_wrapped_dir).resolve()
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "watchdog_keep_patrick_running.log"
    interval_seconds = max(1, args.interval_minutes) * 60
    stale_seconds = max(1, args.stale_minutes) * 60

    write_log(
        "watchdog_started",
        log_path,
        config=args.config,
        check_interval_minutes=args.interval_minutes,
        stale_threshold_minutes=args.stale_minutes,
    )
    write_log("using_alas_wrapped_dir", log_path, path=str(alas_wrapped_dir))
    write_log(
        "strategy",
        log_path,
        detail="monitor log file staleness; relaunch gui.py when bot is paused",
    )

    while True:
        try:
            alas_log = find_alas_log(alas_wrapped_dir, args.config)

            if alas_log is None:
                write_log(
                    "warn_log_file_missing",
                    log_path,
                    config=args.config,
                )
                write_log(
                    "action_relaunch_missing_log",
                    log_path,
                    detail="no matching ALAS log file found; forcing relaunch",
                )
                killed = kill_gui_processes(alas_wrapped_dir)
                if killed:
                    write_log("killed_gui_processes", log_path, pids=killed)
                else:
                    write_log("no_gui_processes_found", log_path)
                time.sleep(3)
                start_gui(alas_wrapped_dir, args.config)
                write_log("launched_gui", log_path, config=args.config)
            else:
                stale_ago = get_log_stale_seconds(alas_log)
                stale_ago_min = stale_ago / 60.0

                if stale_ago < stale_seconds:
                    write_log(
                        "ok_log_active",
                        log_path,
                        config=args.config,
                        stale_minutes=round(stale_ago_min, 2),
                        log_file=alas_log.name,
                    )
                else:
                    write_log(
                        "stale_detected",
                        log_path,
                        config=args.config,
                        stale_minutes=round(stale_ago_min, 2),
                        threshold_minutes=args.stale_minutes,
                        log_file=alas_log.name,
                    )
                    write_log("action_relaunch", log_path, detail="killing gui.py and relaunching")

                    killed = kill_gui_processes(alas_wrapped_dir)
                    if killed:
                        write_log("killed_gui_processes", log_path, pids=killed)
                    else:
                        write_log("no_gui_processes_found", log_path)

                    time.sleep(3)
                    start_gui(alas_wrapped_dir, args.config)
                    write_log("launched_gui", log_path, config=args.config)

                    # Give the bot 30s to produce new log activity
                    time.sleep(30)
                    alas_log_new = find_alas_log(alas_wrapped_dir, args.config)
                    if alas_log_new and get_log_stale_seconds(alas_log_new) < 60:
                        write_log("recovered", log_path, config=args.config, log_file=alas_log_new.name)
                    else:
                        write_log("warn_relaunch_no_activity", log_path, config=args.config)

        except Exception as exc:
            write_log("error", log_path, message=str(exc), error_type=type(exc).__name__)

        time.sleep(interval_seconds)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        logs_dir = Path(__file__).resolve().parents[1] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "watchdog_keep_patrick_running.log"
        write_log("watchdog_stopped", log_path, reason="keyboard_interrupt")
        raise SystemExit(0)
