import os

from image_categorizer import metadata
from image_categorizer import settings as settings_mod
from image_categorizer.categorizer import Categorizer
from image_categorizer.model import IMG_EXTS, SessionModel


class Controller:
    """Framework-free glue between the UI and model/categorizer/settings."""

    def __init__(self, settings: dict):
        self.settings = settings
        self.model = SessionModel()
        self.model.categories = list(settings.get("categories", []))
        self.categorizer = None
        self.source_dir = ""
        self.meta_shown = False
        self.filter_text = ""

    # -- directory/session -------------------------------------------------

    def open_directory(self, path: str) -> None:
        paths = [
            os.path.join(path, n)
            for n in os.listdir(path)
            if n.lower().endswith(IMG_EXTS)
        ]
        if self.settings.get("subfolders"):
            for sub in sorted(os.listdir(path)):
                subp = os.path.join(path, sub)
                if os.path.isdir(subp):
                    paths.extend(
                        os.path.join(subp, n)
                        for n in os.listdir(subp)
                        if n.lower().endswith(IMG_EXTS)
                    )
        paths = sorted(set(paths), key=str.lower)
        self.settings["last_dir"] = path
        if not paths:
            settings_mod.save_settings(self.settings)
            raise ValueError(f"No images found in {path}")
        self.source_dir = path
        self.model.images = paths
        self.model.cursor = 0
        state = settings_mod.load_state(path)
        cursor = state.get("cursor", 0)
        if 0 <= cursor < len(self.model.images):
            self.model.cursor = cursor
        self.model.processed = set(state.get("processed", []))
        self.filter_text = ""
        self.categorizer = Categorizer(self.model, self.settings.get("rename_pattern", ""))
        self.save_all()

    def current_image(self):
        return self.model.current()

    def remaining(self) -> int:
        return self.model.remaining()

    def finished(self) -> bool:
        return self.model.finished()

    def processed_count(self) -> int:
        return len(self.model.processed)

    def thumbnails(self, limit: int = 12) -> list[str]:
        tail = self.model.images[self.model.cursor :]
        if self.filter_text:
            f = self.filter_text.lower()
            tail = [p for p in tail if f in os.path.basename(p).lower()]
        return tail[:limit]

    def jump_to(self, path: str) -> None:
        if path in self.model.images:
            self.model.cursor = self.model.images.index(path)

    def describe_current(self):
        path = self.model.current()
        return metadata.describe(path) if path else None

    # -- actions (each saves session state) ---------------------------------

    def categorize(self, index: int) -> str | None:
        categories = self.model.categories
        if self.categorizer is None or not 0 <= index < len(categories):
            return None
        if self.model.current() is None:
            return None
        self.model.mode = self.settings.get("mode", "move")
        try:
            self.categorizer.handle(categories[index], self.source_dir)
        except (OSError, KeyError, IndexError, ValueError) as e:
            raise RuntimeError(str(e)) from e
        self.save_all()
        return categories[index]

    def skip(self) -> None:
        if self.categorizer is None or self.model.finished():
            return
        self.categorizer.skip()
        self.save_all()

    def undo(self):
        if not self.can_undo():
            return None
        try:
            action = self.categorizer.undo()
        except (OSError, KeyError, IndexError, ValueError) as e:
            raise RuntimeError(str(e)) from e
        if action is None:
            return None
        self.save_all()
        basename = os.path.basename(str(action.dst or action.src or ""))
        return f"Undid {action.op} on {basename}" if basename else f"Undid {action.op}"

    def can_undo(self) -> bool:
        return bool(self.categorizer and self.categorizer.undo_log)

    # -- categories ---------------------------------------------------------

    def add_category(self, name: str) -> tuple[bool, str]:
        if not name:
            return False, "Category name is empty"
        for ch in '<>:"/\\|?*':
            if ch in name:
                return False, f"Category name contains invalid character {ch!r}"
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
            return False, "Category name contains control characters"
        if name.startswith("."):
            return False, "Category name cannot start with a dot"
        if name.endswith((" ", ".")):
            return False, "Category name cannot end with a space or dot"
        if name.lower() in (c.lower() for c in self.model.categories):
            return False, f"Category {name!r} already exists (duplicate)"
        if self.source_dir:
            try:
                os.makedirs(os.path.join(self.source_dir, name), exist_ok=True)
            except OSError as e:
                return False, f"Could not create category folder: {e}"
        self.model.categories.append(name)
        self.settings["categories"] = list(self.model.categories)
        settings_mod.save_settings(self.settings)
        return True, ""

    def categories(self) -> list[str]:
        return list(self.model.categories)

    def save_all(self) -> None:
        settings_mod.save_settings(self.settings)
        if self.source_dir:
            settings_mod.save_state(
                self.source_dir,
                {"cursor": self.model.cursor, "processed": sorted(self.model.processed)},
            )
