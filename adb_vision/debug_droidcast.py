"""Debug DroidCast_raw startup."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from server import _adb_run, ADB_EXECUTABLE, ADB_SERIAL


async def main():
    print(f"Trying to start DroidCast_raw on {ADB_SERIAL}...")

    # Run directly (not backgrounded) to see output
    proc = await asyncio.create_subprocess_exec(
        ADB_EXECUTABLE, "-s", ADB_SERIAL,
        "shell",
        "CLASSPATH=/data/local/tmp/DroidCast_raw.apk",
        "app_process", "/", "ink.mol.droidcast_raw.Main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        print(f"Exit code: {proc.returncode}")
        print(f"Stdout: {stdout.decode(errors='replace')[:1000]}")
        print(f"Stderr: {stderr.decode(errors='replace')[:1000]}")
    except asyncio.TimeoutError:
        print("Process still running after 8s — this is GOOD for a server!")
        proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
