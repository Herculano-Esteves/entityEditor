import json
import os

class SessionManager:
    SESSION_FILE = "session.json"

    @staticmethod
    def save_last_project(path):
        data = {"last_project": path}
        try:
            with open(SessionManager.SESSION_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save session: {e}")

    @staticmethod
    def load_last_project():
        if not os.path.exists(SessionManager.SESSION_FILE):
            return None
        try:
            with open(SessionManager.SESSION_FILE, 'r') as f:
                data = json.load(f)
                return data.get("last_project")
        except Exception as e:
            print(f"Failed to load session: {e}")
            return None
