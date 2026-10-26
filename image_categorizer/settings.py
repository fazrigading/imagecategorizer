import json
from copy import deepcopy
from pathlib import Path

DEFAULTS = {
    "categories": ["infected", "normal"],
    "mode": "move",
    "subfolders": False,
    "theme": "system",
    "last_dir": "",
    "rename_pattern": "{category}_{idx:04d}{ext}",
}
_config_named = "settings.json"
_settings_file = Path.home() / ".imagecategorizer" / _config_named


def config_dir() -> Path:
    return Path.home() / ".imagecategorizer"


def load_settings() -> dict:
    try:
        data = json.loads(_settings_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings must be an object")  # noqa: TRY004
        return {**DEFAULTS, **{k: data[k] for k in DEFAULTS if k in data}}
    except (OSError, ValueError):
        return deepcopy(DEFAULTS)


def save_settings(settings: dict) -> None:
    d = {**DEFAULTS, **settings}
    _settings_file.parent.mkdir(parents=True, exist_ok=True)
    _settings_file.write_text(json.dumps(d, indent=2), encoding="utf-8")


def load_state(src: str) -> dict:
    try:
        d = json.loads((Path(src) / ".imagecategorizer-state.json").read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            raise ValueError("state must be an object")  # noqa: TRY004
        cursor = d.get("cursor", 0)
        if isinstance(cursor, bool) or not isinstance(cursor, int) or cursor < 0:
            cursor = 0
        processed = [str(p) for p in d.get("processed", []) if isinstance(p, str)]
        return {"cursor": cursor, "processed": list(dict.fromkeys(processed))}
    except (OSError, ValueError):
        return {}


def save_state(src: str, state: dict) -> None:
    p = Path(src) / ".imagecategorizer-state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(state), indent=2), encoding="utf-8")


def clear_state(src: str) -> None:
    (Path(src) / ".imagecategorizer-state.json").unlink(missing_ok=True)
