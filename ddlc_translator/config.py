"""Application paths and settings."""
import json
from pathlib import Path

APP = "DDLC Translation Studio"
DATA_DIR = Path.home() / ".ddlc_translation_studio"
SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "rpa_extractor": "unrpa",
    "rpa_args": ["-p", "{output}", "{input}"],
    "rpyc_decompiler": "unrpyc",
    "rpyc_args": ["{input}"],
    "renpy": "renpy",
    "renpy_args": ["{project}", "compile"],
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
    tmp = SETTINGS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_PATH)
