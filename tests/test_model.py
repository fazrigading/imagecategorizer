import os

from image_categorizer.model import SessionModel


def test_load_images_filters_and_sorts(tmp_path):
    (tmp_path / "B.jpeg").write_bytes(b"")
    (tmp_path / "a.jpg").write_bytes(b"")
    (tmp_path / "c.PNG").write_bytes(b"")
    (tmp_path / "d.webp").write_bytes(b"")
    (tmp_path / "readme.txt").write_text("x")
    m = SessionModel()
    assert m.load_images(str(tmp_path)) == 4
    names = [os.path.basename(p) for p in m.images]
    assert names == ["a.jpg", "B.jpeg", "c.PNG", "d.webp"]


def test_sort_is_case_insensitive(tmp_path):
    (tmp_path / "z.jpg").write_bytes(b"")
    (tmp_path / "C.jpg").write_bytes(b"")
    m = SessionModel()
    m.load_images(str(tmp_path))
    names = [os.path.basename(p) for p in m.images]
    assert names == ["C.jpg", "z.jpg"]


def test_current_advances_and_remaining(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"")
    (tmp_path / "b.jpg").write_bytes(b"")
    m = SessionModel()
    m.load_images(str(tmp_path))
    assert m.current() == m.images[0]
    m.advance(m.current())
    assert m.current() == m.images[1]
    assert m.remaining() == 1


def test_finished_when_cursor_at_end(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"")
    m = SessionModel()
    m.load_images(str(tmp_path))
    m.advance(m.images[0])
    assert m.finished()
    assert m.current() is None
    assert m.remaining() == 0


def test_is_image():
    from image_categorizer.model import is_image

    assert is_image("x.JPG")
    assert is_image("x.jfif")
    assert not is_image("x.txt")
    assert not is_image("jpg")
