
import os
import requests
import logging

logger = logging.getLogger("AlasAdminClient")

SERVICE_URL = "http://127.0.0.1:22269"
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "alas_admin_token")

class AlasAdminClient:
    def __init__(self):
        self.token = self._load_token()

    def _load_token(self):
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, "r") as f:
                    return f.read().strip()
        except Exception:
            pass
        return None

    def is_available(self):
        """Check if the admin service is running."""
        try:
            resp = requests.get(SERVICE_URL, timeout=1)
            return resp.status_code == 200
        except Exception:
            return False

    def start_process(self, command):
        """Request the admin service to start a process."""
        if not self.token:
            self.token = self._load_token()
        
        if not self.token:
            logger.error("Admin service token not found.")
            return False

        try:
            resp = requests.post(
                f"{SERVICE_URL}/start",
                json={"command": command},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5
            )
            if resp.status_code == 200:
                return True
            else:
                logger.error(f"Admin service error: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to admin service: {e}")
            return False

    def kill_process(self, regex):
        """Request the admin service to kill a process by regex."""
        if not self.token:
            self.token = self._load_token()
        
        if not self.token:
            logger.error("Admin service token not found.")
            return False

        try:
            resp = requests.post(
                f"{SERVICE_URL}/kill",
                json={"regex": regex},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5
            )
            if resp.status_code == 200:
                return True
            else:
                logger.error(f"Admin service error: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to admin service: {e}")
            return False
