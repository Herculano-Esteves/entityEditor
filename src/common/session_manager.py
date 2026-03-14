"""
SessionManager — persists the last opened project path between launches.

The session file is a small JSON file in the current working directory.
It is intentionally excluded from git via .gitignore.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

SESSION_FILE = "session.json"


class SessionManager:
    """Reads and writes the last-used project path to a local session file."""

    @staticmethod
    def save_last_project(path: str) -> None:
        """Persist *path* as the last opened project."""
        data = {"last_project": path}
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.warning("Could not save session file: %s", e)

    @staticmethod
    def load_last_project() -> str | None:
        """Return the last opened project path, or ``None`` if unavailable."""
        if not os.path.exists(SESSION_FILE):
            return None
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_project")
        except Exception as e:
            logger.warning("Could not read session file: %s", e)
            return None
