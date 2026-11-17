"""Application paths and persisted settings."""
import json
from pathlib import Path

APP = "DDLC Translation Studio"
DATA_DIR = Path.home() / ".ddlc_translation_studio"
SETTINGS_PATH = DATA_DIR / "settings.json"
PROJECTS_ROOT = Path.home() / "DDLC Translation Studio Projects"
MODS_ROOT = Path.home() / "DDLC Mods"

DEFAULT_SETTINGS = {
    "language": "es",
    "theme": "dark",
    "renpy6": "",
    "renpy7": "",
    "renpy8": "",
    "last_base": "",
    "recent_projects": [],
}


def load_settings():
    data = dict(DEFAULT_SETTINGS)
    try:
        loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        loaded = {}
    if isinstance(loaded, dict):
        for key, value in loaded.items():
            if key in data:
                data[key] = value
    return data


def save_settings(settings):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = SETTINGS_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(settings, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    temp.replace(SETTINGS_PATH)
