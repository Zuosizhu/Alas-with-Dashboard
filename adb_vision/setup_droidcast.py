"""Manual DroidCast setup and test script.

Run: cd adb_vision && uv run python setup_droidcast.py
"""
import asyncio
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(__file__))
from server import _adb_run, ADB_EXECUTABLE, ADB_SERIAL

DROIDCAST_APK_LOCAL = os.path.join(
    os.path.dirname(__file__), "..", "alas_wrapped", "bin", "DroidCast",
    "DroidCast_raw-release-1.0.apk"
)
DROIDCAST_APK_REMOTE = "/data/local/tmp/DroidCast_raw.apk"
DROIDCAST_PORT = 53516


async def setup_and_test():
    print(f"ADB: {ADB_EXECUTABLE}")
    print(f"Serial: {ADB_SERIAL}")
    print(f"APK: {DROIDCAST_APK_LOCAL} (exists={os.path.isfile(DROIDCAST_APK_LOCAL)})")

    # 1. Check emulator
    try:
        state = await _adb_run("get-state", timeout=5.0)
        print(f"1. Emulator state: {state.decode().strip()}")
    except Exception as e:
        print(f"1. FAIL: Cannot reach emulator: {e}")
        return

    # 2. Push APK
    print("2. Pushing DroidCast APK...")
    try:
        proc = await asyncio.create_subprocess_exec(
            ADB_EXECUTABLE, "-s", ADB_SERIAL,
            "push", DROIDCAST_APK_LOCAL, DROIDCAST_APK_REMOTE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
        print(f"   Push result: {stdout.decode().strip()} {stderr.decode().strip()}")
    except Exception as e:
        print(f"   Push FAILED: {e}")
        return

    # 3. Kill existing DroidCast processes
    print("3. Killing old DroidCast processes...")
    try:
        await _adb_run("shell", "pkill", "-f", "droidcast_raw", timeout=5.0)
        print("   Killed existing process")
    except Exception:
        print("   No existing process (or pkill not available)")

    await asyncio.sleep(1)

    # 4. Start DroidCast_raw in background
    print("4. Starting DroidCast_raw server on device...")
    try:
        proc = await asyncio.create_subprocess_exec(
            ADB_EXECUTABLE, "-s", ADB_SERIAL,
            "shell",
            "nohup", "sh", "-c",
            f"CLASSPATH={DROIDCAST_APK_REMOTE} app_process / ink.mol.droidcast_raw.Main",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        # Don't wait for completion — it's a background server
        # Give it a moment to start
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            print(f"   Process exited (unexpected): stdout={stdout[:200]}, stderr={stderr[:200]}")
        except asyncio.TimeoutError:
            print("   DroidCast_raw process is running (good - it didn't exit)")
    except Exception as e:
        print(f"   Start FAILED: {e}")
        return

    await asyncio.sleep(2)

    # 5. Forward port
    print(f"5. Forwarding port tcp:{DROIDCAST_PORT}...")
    try:
        await _adb_run("forward", f"tcp:{DROIDCAST_PORT}", f"tcp:{DROIDCAST_PORT}", timeout=5.0)
        print(f"   Port {DROIDCAST_PORT} forwarded")
    except Exception as e:
        print(f"   Forward FAILED: {e}")
        return

    # 6. Test connectivity
    print("6. Testing DroidCast HTTP endpoint...")
    for endpoint in ["/", "/preview", "/screenshot"]:
        url = f"http://127.0.0.1:{DROIDCAST_PORT}{endpoint}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
                print(f"   GET {endpoint}: status=200, {len(data)} bytes, content-type={resp.headers.get('Content-Type', 'unknown')}")
                if endpoint == "/preview" and len(data) > 5000:
                    # Save it!
                    out_path = os.path.join(os.path.dirname(__file__), "test_droidcast_preview.png")
                    with open(out_path, "wb") as f:
                        f.write(data)
                    print(f"   SAVED real screenshot to: {out_path} ({len(data)} bytes)")
                    print(f"   PNG header check: {data[:4] == b'\\x89PNG'}")
        except urllib.error.HTTPError as e:
            print(f"   GET {endpoint}: HTTP {e.code} (expected for / endpoint)")
        except Exception as e:
            print(f"   GET {endpoint}: FAILED: {e}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(setup_and_test())
