import os

from PIL import Image

_TAG_MAKE, _TAG_MODEL, _TAG_DATETIME = 0x010F, 0x0110, 0x0132


def describe(path: str) -> str:
    name = os.path.basename(path)
    try:
        with Image.open(path) as img:
            lines = [
                f"File: {name}",
                f"Format: {img.format}",
                f"Dimensions: {img.width}x{img.height}",
                f"Size: {os.path.getsize(path) / 1024:.0f} KiB",
            ]
            exif = img.getexif()
            for label, tag in (("Make", _TAG_MAKE), ("Model", _TAG_MODEL), ("DateTime", _TAG_DATETIME)):
                value = exif.get(tag)
                if value:
                    lines.append(f"{label}: {value}")
            return "\n".join(lines)
    except Exception:
        return f"File: {name}\n(unreadable)"
