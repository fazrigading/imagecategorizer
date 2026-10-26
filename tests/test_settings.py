import json

from image_categorizer import settings


def _monkeypatched_file(tmp_path, monkeypatch):
    p = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "_settings_file", p)
    return p


def test_defaults_shape(tmp_path, monkeypatch):
    _monkeypatched_file(tmp_path, monkeypatch)
    s = settings.load_settings()
    assert s == settings.DEFAULTS
    assert set(s) == set(settings.DEFAULTS)


def test_roundtrip_and_unknown_key_drop(tmp_path, monkeypatch):
    p = _monkeypatched_file(tmp_path, monkeypatch)
    s = dict(settings.DEFAULTS)
    s["theme"] = "dark"
    s["extra_junk"] = 1
    settings.save_settings(s)
    merged = {**settings.DEFAULTS, "theme": "dark", "extra_junk": 1}
    p.write_text(json.dumps(merged, indent=2))
    loaded = settings.load_settings()
    assert loaded["theme"] == "dark"
    assert "extra_junk" not in loaded


def test_corrupt_settings_returns_defaults(tmp_path, monkeypatch):
    p = _monkeypatched_file(tmp_path, monkeypatch)
    p.write_text("{not json]")
    assert settings.load_settings() == settings.DEFAULTS


def test_state_roundtrip(tmp_path):
    src = tmp_path / "src"
    settings.save_state(str(src), {"cursor": 3, "processed": ["/a.jpg"]})
    assert settings.load_state(str(src)) == {"cursor": 3, "processed": ["/a.jpg"]}
    assert json.loads((src / ".imagecategorizer-state.json").read_text()) == \
        {"cursor": 3, "processed": ["/a.jpg"]}


def test_state_corrupt_or_missing(tmp_path, monkeypatch):
    src = tmp_path / "broken"
    src.mkdir()
    (src / ".imagecategorizer-state.json").write_text("garbage")
    assert settings.load_state(str(src)) == {}


def test_state_cursor_coercion(tmp_path, monkeypatch):
    src = tmp_path / "src2"
    src.mkdir()
    (src / ".imagecategorizer-state.json").write_text(
        json.dumps({"cursor": -1, "processed": ["x"]})
    )
    assert settings.load_state(str(src)) == {"cursor": 0, "processed": ["x"]}


def test_clear_state(tmp_path):
    src = tmp_path / "src3"
    settings.save_state(str(src), {"cursor": 1, "processed": []})
    settings.clear_state(str(src))
    assert settings.load_state(str(src)) == {}
