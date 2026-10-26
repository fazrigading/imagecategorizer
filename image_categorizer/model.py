import os

IMG_EXTS = (".jpg", ".jpeg", ".png", ".jfif", ".bmp", ".webp")


def is_image(filename: str) -> bool:
    return filename.lower().endswith(IMG_EXTS)


class SessionModel:
    def __init__(self):
        self.categories = ["infected", "normal"]
        self.images = []
        self.cursor = 0
        self.processed = set()
        self.mode = "move"

    def load_images(self, directory: str) -> int:
        self.images = sorted(
            (os.path.join(directory, name) for name in os.listdir(directory) if is_image(name)),
            key=lambda p: os.path.basename(p).lower(),
        )
        self.cursor = 0
        return len(self.images)

    def current(self):
        if self.cursor < len(self.images):
            return self.images[self.cursor]
        return None

    def advance(self, _path: str = "") -> None:
        self.cursor += 1

    def remaining(self) -> int:
        return len(self.images) - self.cursor

    def finished(self) -> bool:
        return self.cursor >= len(self.images)
