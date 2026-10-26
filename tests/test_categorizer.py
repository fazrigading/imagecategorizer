import os

import pytest

from image_categorizer.categorizer import Categorizer
from image_categorizer.model import SessionModel


def _workspace(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for n in ("a.jpg", "b.jpg", "c.png"):
        (src / n).write_bytes(b"data")
    m = SessionModel()
    m.load_images(str(src))
    return src, m


def test_move_to_category(tmp_path):
    src, m = _workspace(tmp_path)
    c = Categorizer(m)
    a = c.handle("cats", str(src))
    assert a.op == "move"
    assert (src / "cats" / "a.jpg").is_file()
    assert not (src / "a.jpg").exists()
    assert os.path.basename(m.current()) == "b.jpg"
    assert str(src / "cats" / "a.jpg") in {os.fspath(x) for x in m.processed}


def test_copy_mode_keeps_original_and_advances(tmp_path):
    src, m = _workspace(tmp_path)
    m.mode = "copy"
    c = Categorizer(m)
    a = c.handle("cats", str(src))
    assert a.op == "copy"
    assert (src / "a.jpg").is_file() and (src / "cats" / "a.jpg").is_file()
    assert os.path.basename(m.current()) == "b.jpg"


def test_collision_gets_numeric_suffix(tmp_path):
    src, m = _workspace(tmp_path)
    (src / "cats").mkdir()
    (src / "cats" / "a.jpg").write_bytes(b"existing")
    c = Categorizer(m)
    c.handle("cats", str(src))
    assert (src / "cats" / "a_1.jpg").is_file()


def test_rename_pattern(tmp_path):
    src, m = _workspace(tmp_path)
    c = Categorizer(m, rename_pattern="{category}_{idx:04d}{ext}")
    c.handle("cats", str(src))
    assert (src / "cats" / "cats_0001.jpg").is_file()


def test_skip_then_undo_reverts_move(tmp_path):
    src, m = _workspace(tmp_path)
    c = Categorizer(m)
    a1 = c.handle("cats", str(src))
    assert c.skip(str(src)).op == "skip"
    assert os.path.basename(m.current()) == "c.png"
    rev_skip = c.undo()
    assert rev_skip.op == "skip"
    assert os.path.basename(m.current()) == "b.jpg"
    rev_move = c.undo()
    assert rev_move.op == "move"
    assert (src / "a.jpg").is_file()
    assert not (src / "cats" / "a.jpg").exists()
    assert m.cursor == a1.cursor_before
    assert str(src / "cats" / "a.jpg") not in {os.fspath(x) for x in m.processed}


def test_undo_copied_file_is_removed(tmp_path):
    src, m = _workspace(tmp_path)
    m.mode = "copy"
    c = Categorizer(m)
    c.handle("cats", str(src))
    c.undo()
    assert not (src / "cats" / "a.jpg").exists()
    assert (src / "a.jpg").is_file()


def test_undo_empty_returns_none(tmp_path):
    _src, m = _workspace(tmp_path)
    assert Categorizer(m).undo() is None


def test_no_current_image_raises(tmp_path):
    src, m = _workspace(tmp_path)
    for p in list(m.images):
        m.advance(p)
    with pytest.raises(RuntimeError):
        Categorizer(m).handle("cats", str(src))
