
import os
import sys
import uvicorn
import secrets
import subprocess
import logging
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("AlasAdminService")

# Configuration
HOST = "127.0.0.1"
PORT = 22269
_SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(_SERVICE_DIR, "alas_admin_token")

# Generate and save a secure token (path must match AlasAdminClient expectation)
AUTH_TOKEN = secrets.token_hex(32)
with open(TOKEN_FILE, "w") as f:
    f.write(AUTH_TOKEN)
logger.info(f"Admin service started. Token saved to {TOKEN_FILE}")

async def check_auth(request):
    token = request.headers.get("Authorization")
    if token != f"Bearer {AUTH_TOKEN}":
        return False
    return True

async def root(request):
    return JSONResponse({"status": "running", "service": "AlasAdminService"})

async def start_process(request):
    if not await check_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    data = await request.json()
    command = data.get("command")
    
    if not command:
        return JSONResponse({"error": "No command provided"}, status_code=400)

    logger.info(f"Executing: {command}")
    
    try:
        # Use subprocess.Popen to start the process detached
        # This allows the service to keep running even if the child process does whatever
        subprocess.Popen(command, shell=True, close_fds=True, start_new_session=True)
        return JSONResponse({"status": "success", "executed": command})
    except Exception as e:
        logger.error(f"Failed to execute: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

async def kill_process(request):
    if not await check_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    data = await request.json()
    regex = data.get("regex")
    
    if not regex:
        return JSONResponse({"error": "No regex provided"}, status_code=400)

    logger.info(f"Killing process by regex: {regex}")

    try:
        # Match by CommandLine (same semantics as platform_windows fallback). Escape ' for PowerShell.
        safe_regex = regex.replace("'", "''")
        ps_command = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -and $_.CommandLine -match '" + safe_regex + "' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], check=False)
        return JSONResponse({"status": "success", "killed": regex})
    except Exception as e:
        logger.error(f"Failed to kill: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

app = Starlette(debug=False, routes=[
    Route('/', root),
    Route('/start', start_process, methods=['POST']),
    Route('/kill', kill_process, methods=['POST']),
])

if __name__ == "__main__":
    # Ensure we are in the script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run(app, host=HOST, port=PORT)
