import os
import sys
from pathlib import Path


APP_NAME = "PikPakTextImporter"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return app_root()


def user_data_dir() -> Path:
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / APP_NAME
    return Path.home() / f".{APP_NAME}"


def default_config_path() -> Path:
    return user_data_dir() / "config" / "account.json"


def default_session_path() -> Path:
    return user_data_dir() / "session" / "session.json"
