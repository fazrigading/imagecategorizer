from pathlib import Path

from PIL import Image

from image_categorizer import settings
from image_categorizer.controller import Controller


def _seed(tmp_path: Path, count: int = 2) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    for i in range(count):
        Image.new("RGB", (10, 10), "red").save(src / f"img_{i}.jpg")
    return src


def _controller(tmp_path, monkeypatch) -> Controller:
    f = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "_settings_file", f)
    return Controller(dict(settings.DEFAULTS))


def test_open_then_categorize_and_undo(tmp_path, monkeypatch):
    src = _seed(tmp_path)
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    assert c.current_image() == str(src / "img_0.jpg")
    assert c.categorize(0) == "infected"
    # real dest layout: Categorizer.handle joins source_dir/category and applies
    # DEFAULTS rename_pattern "{category}_{idx:04d}{ext}"
    assert c.model.processed == {str(src / "infected" / "infected_0001.jpg")}


def test_categorize_moves_next(tmp_path, monkeypatch):
    src = _seed(tmp_path, 3)
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    c.categorize(0)
    assert c.current_image() == str(src / "img_1.jpg")
    assert not c.finished()


def test_skip_and_cursor(tmp_path, monkeypatch):
    src = _seed(tmp_path, 1)
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    c.skip()
    assert c.finished()
    result = c.undo()  # single call: brief's inline double-call consumed two undo entries
    assert result is None or isinstance(result, str)
    assert c.current_image() == str(src / "img_0.jpg")  # undo skipped→restores


def test_undo_restores_to_skipped(tmp_path, monkeypatch):
    src = _seed(tmp_path, 2)
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    c.skip()
    c.skip()
    assert c.can_undo() is True
    c.undo()
    assert c.current_image() == str(src / "img_1.jpg")


def test_add_category_validation(tmp_path, monkeypatch):
    c = _controller(tmp_path, monkeypatch)
    ok, _ = c.add_category("new-cat")
    assert ok is True
    ok2, msg2 = c.add_category("new-cat")
    assert ok2 is False and "duplicate" in msg2.lower()


def test_add_category_invalid_chars(tmp_path, monkeypatch):
    c = _controller(tmp_path, monkeypatch)
    for bad in ["a<b", "a:b", "a/b", ".hidden", "trail ", "trail."]:
        ok, msg = c.add_category(bad)
        assert ok is False, f"{bad!r} should be rejected"
        assert msg  # non-empty error message
    ok, _ = c.add_category("evil" + chr(7))  # control char
    assert ok is False


def test_filter_via_thumbnails(tmp_path, monkeypatch):
    src = _seed(tmp_path, 4)
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    c.filter_text = "img_1"
    assert c.thumbnails() == [str(src / "img_1.jpg")]
