import json
import os
from pathlib import Path

STATE_FILENAME = ".imagecategorizer-state.json"

DEFAULTS = {
    "last_dir": "",
    "categories": ["infected", "normal"],
    "mode": "move",
    "rename_pattern": "",
    "use_subfolders": False,
}


def config_dir() -> Path:
    return Path.home() / ".imagecategorizer"


_settings_file: Path = config_dir() / "settings.json"


def load_settings() -> dict:
    try:
        saved = json.loads(_settings_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(DEFAULTS)
    if not isinstance(saved, dict):
        return dict(DEFAULTS)
    # unknown keys dropped so a hand-edited file cannot poison the app
    return {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}


def save_settings(new_settings: dict) -> None:
    _settings_file.parent.mkdir(parents=True, exist_ok=True)
    filtered = {k: v for k, v in new_settings.items() if k in DEFAULTS}
    _settings_file.write_text(json.dumps(filtered, indent=2), encoding="utf-8")


def _state_file(source_dir: str) -> str:
    return os.path.join(source_dir, STATE_FILENAME)


def load_state(source_dir: str) -> dict:
    if not os.path.isfile(_state_file(source_dir)):
        return {}
    try:
        with open(_state_file(source_dir), encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def save_state(source_dir: str, state: dict) -> None:
    with open(_state_file(source_dir), "w", encoding="utf-8") as f:
        json.dump(state, f)


def clear_state(source_dir: str) -> None:
    try:
        os.remove(_state_file(source_dir))
    except FileNotFoundError:
        pass
