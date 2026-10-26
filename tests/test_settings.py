import json
import os

from image_categorizer import settings


def test_load_settings_returns_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "_settings_file", tmp_path / "settings.json")
    assert settings.load_settings() == dict(settings.DEFAULTS)


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "_settings_file", tmp_path / "settings.json")
    settings.save_settings({"mode": "copy", "categories": ["good", "bad"]})
    s = settings.load_settings()
    assert s["mode"] == "copy"
    assert s["categories"] == ["good", "bad"]


def test_load_merges_defaults_with_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "_settings_file", tmp_path / "settings.json")
    settings._settings_file.write_text(json.dumps({"mode": "copy"}))
    s = settings.load_settings()
    assert s["mode"] == "copy"
    assert s["categories"] == settings.DEFAULTS["categories"]
    assert s["last_dir"] == ""


def test_load_corrupt_file_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "_settings_file", tmp_path / "settings.json")
    settings._settings_file.write_text("not json {{{")
    assert settings.load_settings() == dict(settings.DEFAULTS)


def test_state_roundtrip(tmp_path):
    src = str(tmp_path)
    settings.save_state(src, {"cursor": 3, "processed": ["a.jpg"]})
    assert settings.load_state(src) == {"cursor": 3, "processed": ["a.jpg"]}
    assert os.path.isfile(os.path.join(src, ".imagecategorizer-state.json"))
    settings.clear_state(src)
    assert settings.load_state(src) == {}


def test_state_corrupt_or_absent_yields_empty(tmp_path):
    src = tmp_path / "proj"
    src.mkdir()
    (src / ".imagecategorizer-state.json").write_text("]]] bad")
    assert settings.load_state(str(src)) == {}
    assert settings.load_state(str(tmp_path / "nope")) == {}
