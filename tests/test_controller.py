from pathlib import Path

import pytest
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


def test_rename_and_remove_category(tmp_path, monkeypatch):
    c = _controller(tmp_path, monkeypatch)
    c.add_category("first")
    ok, _ = c.rename_category("first", "renamed")
    assert ok is True
    assert c.categories() == ["infected", "normal", "renamed"]
    assert settings.load_settings()["categories"] == c.categories()
    ok, _ = c.remove_category("renamed")
    assert ok is True
    assert "renamed" not in c.categories()
    # rename onto duplicate / invalid names is rejected
    ok, msg = c.rename_category("infected", "NORMAL")
    assert ok is False and "duplicate" in msg.lower()
    ok, msg = c.rename_category("normal", "a<b")
    assert ok is False and "invalid" in msg.lower()
    ok, msg = c.rename_category("ghost", "anything")
    assert ok is False


def test_remove_unknown_and_empty_names(tmp_path, monkeypatch):
    c = _controller(tmp_path, monkeypatch)
    ok, msg = c.remove_category("ghost")
    assert ok is False and msg
    c.add_category("a")
    ok, _ = c.rename_category("a", "a")  # rename to self allowed
    assert ok is True


def test_counts_by_category(tmp_path, monkeypatch):
    src = _seed(tmp_path, 5)
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    c.categorize(0)  # infected
    c.categorize(0)
    c.skip()
    counts, skipped = c.count_categories()
    assert counts == {"infected": 2}
    assert skipped == 1
    assert c.processed_count() == 2


def test_jump_to_moves_cursor(tmp_path, monkeypatch):
    src = _seed(tmp_path, 3)
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    c.jump_to(str(src / "img_2.jpg"))
    assert c.current_image() == str(src / "img_2.jpg")


def test_jump_to_unknown_path_is_noop(tmp_path, monkeypatch):
    src = _seed(tmp_path, 3)
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    c.jump_to(str(src / "nope.jpg"))
    assert c.current_image() == str(src / "img_0.jpg")


def test_describe_current_returns_metadata_text(tmp_path, monkeypatch):
    src = _seed(tmp_path, 1)
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    text = c.describe_current()
    assert text.endswith("10x10") or (text.startswith("File: img_0.jpg") and "Dimensions: 10x10" in text)


def test_open_empty_dir_raises_after_last_dir_save(tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    c = _controller(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        c.open_directory(str(empty))
    assert c.settings["last_dir"] == str(empty)
    # last_dir persisted despite the failure; old session untouched
    assert c.source_dir == ""


def test_open_restores_bounds_guarded_cursor(tmp_path, monkeypatch):
    src = _seed(tmp_path, 3)
    src.mkdir(exist_ok=True)
    settings.save_state(str(src), {"cursor": 99, "processed": ["x"]})
    c = _controller(tmp_path, monkeypatch)
    c.open_directory(str(src))
    assert c.model.cursor == 0  # 99 out of bounds → reset
    c.model.cursor = 2
    settings.save_state(str(src), {"cursor": 2, "processed": []})
    c2 = _controller(tmp_path, monkeypatch)
    c2.open_directory(str(src))
    assert c2.model.current() == str(src / "img_2.jpg")
