from PIL import Image

from image_categorizer.metadata import describe


def test_describe_simple_png(tmp_path):
    p = tmp_path / "shot.png"
    Image.new("RGB", (64, 32), "red").save(p)
    text = describe(str(p))
    assert "File: shot.png" in text
    assert "Format: PNG" in text
    assert "Dimensions: 64x32" in text
    assert "Size:" in text
    assert "Make:" not in text


def test_describe_jpeg_with_exif(tmp_path):
    p = tmp_path / "shot.jpg"
    img = Image.new("RGB", (10, 10), "blue")
    exif = img.getexif()
    exif[0x0110] = "ACME-Cam"  # Model
    exif[0x010F] = "ACME"  # Make
    img.save(p, exif=exif)
    text = describe(str(p))
    assert "Model: ACME-Cam" in text
    assert "Make: ACME" in text


def test_describe_unreadable_never_raises(tmp_path):
    p = tmp_path / "broken.jpg"
    p.write_bytes(b"\x00\x01not an image")
    text = describe(str(p))
    assert "File: broken.jpg" in text
    assert "unreadable" in text
