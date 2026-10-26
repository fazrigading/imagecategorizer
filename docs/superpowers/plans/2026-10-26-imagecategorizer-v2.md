# imagecategorizer v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-file Tkinter image triage app into a multi-module package with custom categories, a zoom/pan viewer, undo/skip/copy-move, session persistence, a metadata panel, and a PyPI + .exe + AppImage release pipeline.

**Architecture:** Pure-logic modules (`model`, `categorizer`, `settings`, `metadata`) hold no Tk code and are covered by pytest. GUI modules (`app`, `viewer`) are thin wiring over Canvas. One config file in `~/.imagecategorizer/settings.json`; per-project resume state inside the source directory.

**Tech Stack:** Python ≥3.9, Tkinter (stdlib), Pillow (only third-party runtime dep), setuptools, pytest, ruff, PyInstaller for binaries.

**Spec:** `docs/superpowers/specs/2026-10-26-imagecategorizer-v2-design.md`

## Global Constraints

- Python floor `>=3.9`; single third-party runtime dependency: `Pillow>=10`.
- Package name (PyPI) `imagecategorizer`; import name `image_categorizer`; command `imagecategorizer`.
- Version lives only in `image_categorizer/__init__.py` as `__version__`; pyproject reads it dynamically.
- Resume state file named exactly `.imagecategorizer-state.json`, stored inside the source directory.
- Settings file: `~/.imagecategorizer/settings.json`. Defaults: `categories` starts as `["infected", "normal"]` (parity with current app), `mode` is `"move"`.
- Image extensions: `.jpg`, `.jpeg`, `.png`, `.jfif`, `.bmp`, `.webp` (case-insensitive; current app only knows three).
- All image lists sorted case-insensitively (current app uses raw `os.listdir` order).
- No new GUI toolkits, no asyncio/threads.
- Tests must run without a display.
- `ruff check image_categorizer tests` clean at every commit; no ruff config file introduced.

---

### Task 1: Package skeleton, pyproject, entry point (behavior unchanged)

**Files:**
- Create: `image_categorizer/__init__.py`
- Create: `image_categorizer/app.py` (content = current `main.py`, imports adjusted)
- Create: `pyproject.toml`
- Modify: `.gitignore` (add `dist/`, `build/`, `*.spec`)
- Test: `tests/test_package.py`
- Untouched: `main.py` stays and keeps working until Task 5.

**Interfaces:**
- Produces: importable `image_categorizer` with `__version__`; console command `imagecategorizer` → `image_categorizer.app:main()`.

- [ ] **Step 1: Create package with version and moved app module**

`image_categorizer/__init__.py`:

```python
__version__ = "0.2.0"
```

Create `image_categorizer/app.py`: copy the entire content of `main.py`, then change exactly:

1. All original imports stay at the top; add `from . import __version__`.
2. Rename class `GImageCategorizer` → `ImageCategorizerApp` (definition + both `__main__` usages).
3. Replace the `if __name__ == '__main__':` bottom block with:

```python
def main():
    root = Tk()
    app = ImageCategorizerApp(root)
    root.configure(background="black")
    root.mainloop()


if __name__ == "__main__":
    main()
```

Do not touch titles, geometry, keybinds — behavior must be identical.

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "imagecategorizer"
description = "Fast single-image triage for classification datasets"
readme = "README.md"
requires-python = ">=3.9"
dependencies = ["Pillow>=10"]
dynamic = ["version"]

[project.scripts]
imagecategorizer = "image_categorizer.app:main"

[tool.setuptools.dynamic]
version = { attr = "image_categorizer.__version__" }

[tool.setuptools.packages.find]
include = ["image_categorizer*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Append to `.gitignore`:

```
dist/
build/
*.spec
```

- [ ] **Step 2: Write package smoke test**

`tests/test_package.py`:

```python
import image_categorizer


def test_package_exports_version():
    assert image_categorizer.__version__ == "0.2.0"


def test_app_module_exposes_main():
    from image_categorizer.app import main

    assert callable(main)
```

- [ ] **Step 3: Install and verify behavior unchanged**

Run: `pip install -e . && python -m pytest tests/test_package.py -v`
Expected: 2 PASS; `which imagecategorizer` returns a path.

Run `imagecategorizer` by hand, select any folder, press `o`/`p` — behaves exactly as before. Close it.

- [ ] **Step 4: Commit**

```bash
git add image_categorizer/ pyproject.toml tests/ .gitignore
git commit -m "feat: restructure into package with console entry point"
```

---

### Task 2: settings — app config + per-project resume state

**Files:**
- Create: `image_categorizer/settings.py`
- Test: `tests/test_settings.py`

**Interfaces:**
- Produces:
  - `DEFAULTS: dict` — `{"last_dir": "", "categories": ["infected", "normal"], "mode": "move", "rename_pattern": "", "use_subfolders": False}`
  - `config_dir() -> Path` — always `Path.home() / ".imagecategorizer"`
  - module attribute `_settings_file: Path` (monkeypatch target in tests; real value `config_dir() / "settings.json"`)
  - `load_settings() -> dict` — DEFAULTS merged under saved file; unknown keys dropped; corrupt file → DEFAULTS
  - `save_settings(settings: dict) -> None`
  - `load_state(source_dir: str) -> dict` — keys `cursor: int`, `processed: list[str]`; `{}` if missing/corrupt
  - `save_state(source_dir: str, state: dict) -> None` — writes `.imagecategorizer-state.json` inside `source_dir`
  - `clear_state(source_dir: str) -> None`

- [ ] **Step 1: Write failing tests**

`tests/test_settings.py`:

```python
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
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_settings.py -v`
Expected: FAIL with `ImportError: cannot import name 'settings'`

- [ ] **Step 3: Implement**

`image_categorizer/settings.py`:

```python
import json
import os
from pathlib import Path

STATE_FILENAME = ".imagecategorizer-state.json"

DEFAULTS = {
    "last_dir": "",
    "categories": ["infected", "normal"],
    "mode": "move",
    "rename_pattern": "",
    "use_subfolders": False,
}


def config_dir() -> Path:
    return Path.home() / ".imagecategorizer"


_settings_file: Path = config_dir() / "settings.json"


def load_settings() -> dict:
    try:
        saved = json.loads(_settings_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(DEFAULTS)
    if not isinstance(saved, dict):
        return dict(DEFAULTS)
    # unknown keys dropped so a hand-edited file cannot poison the app
    return {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}


def save_settings(new_settings: dict) -> None:
    _settings_file.parent.mkdir(parents=True, exist_ok=True)
    filtered = {k: v for k, v in new_settings.items() if k in DEFAULTS}
    _settings_file.write_text(json.dumps(filtered, indent=2), encoding="utf-8")


def _state_file(source_dir: str) -> str:
    return os.path.join(source_dir, STATE_FILENAME)


def load_state(source_dir: str) -> dict:
    if not os.path.isfile(_state_file(source_dir)):
        return {}
    try:
        with open(_state_file(source_dir), encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def save_state(source_dir: str, state: dict) -> None:
    with open(_state_file(source_dir), "w", encoding="utf-8") as f:
        json.dump(state, f)


def clear_state(source_dir: str) -> None:
    try:
        os.remove(_state_file(source_dir))
    except FileNotFoundError:
        pass
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest tests/test_settings.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add image_categorizer/settings.py tests/test_settings.py
git commit -m "feat: settings module (app config + per-project resume state)"
```

---

### Task 3: model — image list, cursor, processed set

**Files:**
- Create: `image_categorizer/model.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Consumes: nothing (standalone; no settings import).
- Produces: `SessionModel` and `is_image(filename: str) -> bool`. `SessionModel` attributes: `categories: list[str]`, `images: list[str]` (absolute, case-insensitive sort), `cursor: int`, `processed: set[str]` (destination paths), `mode: str`. Methods:
  - `load_images(directory: str) -> int` (replaces `images`, `cursor = 0`, returns count)
  - `current() -> str | None` (None when done)
  - `advance(path: str) -> None` (cursor += 1; `path` unused, kept for callers' symmetry with categorizer ops)
  - `remaining() -> int`
  - `finished() -> bool`

- [ ] **Step 1: Write failing tests**

`tests/test_model.py`:

```python
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
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'SessionModel'`

- [ ] **Step 3: Implement**

`image_categorizer/model.py`:

```python
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
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest tests/test_model.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add image_categorizer/model.py tests/test_model.py
git commit -m "feat: session model (image list, cursor, processed set)"
```

---

### Task 4: categorizer — copy/move/skip/undo with rename + collision suffix

**Files:**
- Create: `image_categorizer/categorizer.py`
- Test: `tests/test_categorizer.py`

**Interfaces:**
- Consumes: `SessionModel` (Task 3: `.current()`, `.advance(path)`, `.processed`, `.mode`).
- Produces:
  - `Action` dataclass: `op: str` (`"move"|"copy"|"skip"`), `src: str|None`, `dst: str|None`, `cursor_before: int`
  - `Categorizer(model, rename_pattern: str = "")`:
    - `handle(category: str, source_dir: str) -> Action` — copy or move per `model.mode`; destination dir `source_dir/category` created with `os.makedirs(..., exist_ok=True)`; non-pattern name = `basename(src)`; pattern name = `pattern.format(category=..., idx=per-category-sequence, ext=original extension)`; collision → `_1`, `_2` suffix before ext; success → `model.advance(src)`, `model.processed.add(dst)`
    - `skip(source_dir: str) -> Action` — advance only, recorded for undo
    - `undo() -> Action | None` — move: `os.replace(dst, src)`; copy: remove dst; skip: no file op; cursor restored to `cursor_before`; `processed.discard(dst)`. Returns `None` when log empty.
    - Failed file ops raise `OSError` (app turns it into an error dialog); undo log untouched on failure.

- [ ] **Step 1: Write failing tests**

`tests/test_categorizer.py`:

```python
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
    assert src / "cats" / "a.jpg" in {os.fspath(x) for x in m.processed}


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
    assert (src / "cats" / "a.jpg") not in {os.fspath(x) for x in m.processed}


def test_undo_copied_file_is_removed(tmp_path):
    src, m = _workspace(tmp_path)
    m.mode = "copy"
    c = Categorizer(m)
    c.handle("cats", str(src))
    c.undo()
    assert not (src / "cats" / "a.jpg").exists()
    assert (src / "a.jpg").is_file()


def test_undo_empty_returns_none(tmp_path):
    src, m = _workspace(tmp_path)
    assert Categorizer(m).undo() is None


def test_no_current_image_raises(tmp_path):
    src, m = _workspace(tmp_path)
    for p in list(m.images):
        m.advance(p)
    with pytest.raises(RuntimeError):
        Categorizer(m).handle("cats", str(src))
```

- [ ] **Step 2: Run tests, verify failure**

Run: `python -m pytest tests/test_categorizer.py -v`
Expected: FAIL with `ImportError: cannot import name 'Categorizer'`

- [ ] **Step 3: Implement**

`image_categorizer/categorizer.py`:

```python
import os
import shutil
from collections import deque
from dataclasses import dataclass


@dataclass
class Action:
    op: str
    src: str | None
    dst: str | None
    cursor_before: int


def _collide(dst: str) -> str:
    if not os.path.exists(dst):
        return dst
    base, ext = os.path.splitext(dst)
    n = 1
    while os.path.exists(f"{base}_{n}{ext}"):
        n += 1
    return f"{base}_{n}{ext}"


class Categorizer:
    """File ops for triage. Failed ops raise OSError and leave the undo log
    untouched; app layer shows the error dialog."""

    def __init__(self, model, rename_pattern: str = ""):
        self.model = model
        self.rename_pattern = rename_pattern
        self.undo_log = deque(maxlen=50)
        self._rename_index = {}

    def handle(self, category: str, source_dir: str) -> Action:
        src = self.model.current()
        if src is None:
            raise RuntimeError("no current image")
        cat_dir = os.path.join(source_dir, category)
        os.makedirs(cat_dir, exist_ok=True)
        if self.rename_pattern:
            ext = os.path.splitext(src)[1]
            idx = self._rename_index.get(category, 0) + 1
            self._rename_index[category] = idx
            name = self.rename_pattern.format(category=category, idx=idx, ext=ext)
        else:
            name = os.path.basename(src)
        dst = _collide(os.path.join(cat_dir, name))
        cursor_before = self.model.cursor
        if self.model.mode == "copy":
            shutil.copy2(src, dst)
            op = "copy"
        else:
            os.replace(src, dst)
            op = "move"
        self.model.advance(src)
        self.model.processed.add(dst)
        action = Action(op, src, dst, cursor_before)
        self.undo_log.append(action)
        return action

    def skip(self, _source_dir: str = "") -> Action:
        action = Action("skip", None, None, self.model.cursor)
        self.undo_log.append(action)
        self.model.advance("skip")
        return action

    def undo(self):
        if not self.undo_log:
            return None
        action = self.undo_log.pop()
        if action.op == "move":
            os.replace(str(action.dst), str(action.src))
        elif action.op == "copy":
            if os.path.exists(str(action.dst)):
                os.remove(str(action.dst))
        self.model.cursor = action.cursor_before
        if action.dst is not None:
            self.model.processed.discard(str(action.dst))
        return action
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest -v`
Expected: 15 PASS (2 + 6 + 5 + 8 + previous files' counts; every test in the suite green)

- [ ] **Step 5: Commit**

```bash
git add image_categorizer/categorizer.py tests/test_categorizer.py
git commit -m "feat: categorizer core (copy/move/skip/undo, rename pattern, collision suffix)"
```

---

### Task 5: app rewire — dynamic categories, keybinds, persistence, undo/skip

**Files:**
- Modify: `image_categorizer/app.py` (full rewrite; `main()` and version string style kept)
- Delete: `main.py` (fully replaced by the package)
- Test: none new — Tasks 2-4 unit tests cover logic; manual verification below.

**Interfaces:**
- Consumes: `SessionModel`, `Categorizer`, all six `settings.py` functions.
- Produces: `main() -> None` unchanged. `ImageCategorizerApp(root, viewer=None)` — `viewer=None` keeps the current plain-Label display (viewer arrives in Task 6 and is passed by `main()` there).

Resume semantics (binding decisions): state stores `cursor` (int) and `processed` (list of destination paths). On open: cursor restored if within bounds, else 0. "N images left" = `model.remaining()` against the restored cursor; undercounting after moves that happened before a crash is accepted — the count is informational.

- [ ] **Step 1: Rewrite app.py**

Replace the full content of `image_categorizer/app.py` with:

```python
import os
from tkinter import Tk, messagebox, filedialog, Button, Label, Frame, simpledialog

from PIL import Image, ImageTk

from . import __version__, settings
from .categorizer import Categorizer
from .model import SessionModel

WINDOW_TITLE = f"Gading's Image Categorizer v{__version__}"


class ImageCategorizerApp:
    def __init__(self, root: Tk, viewer=None):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("1600x800")
        self.settings = settings.load_settings()
        self.model = SessionModel()
        self.model.categories = list(self.settings["categories"])
        self.model.mode = self.settings["mode"]
        self.source_dir = ""
        self.categorizer = None
        self.viewer = viewer
        self.photo = None

        self.top_bar = Frame(self.root)
        self.top_bar.pack(side="top", fill="x")
        self.select_button = Button(self.top_bar, text="Select Directory", command=self.select_directory)
        self.select_button.pack(side="left")
        self.mode_button = Button(self.top_bar, text="Mode: Move (click to toggle)", command=self.toggle_mode)
        self.mode_button.pack(side="left", padx=5)
        self.undo_button = Button(self.top_bar, text="Undo (u)", state="disabled", command=self.undo)
        self.undo_button.pack(side="left")

        self.cat_bar = Frame(self.root)
        self.cat_bar.pack(side="top", fill="x")
        self.add_category_button = Button(self.cat_bar, text="+ Add category", command=self.add_category_dialog)
        self.add_category_button.pack(side="left")
        self.cat_buttons = {}
        self._rebuild_category_buttons()

        if self.viewer is None:
            self.image_label = Label(self.root)
            self.image_label.pack(expand=True, fill="both")

        self.image_status = Label(self.root, text="Select a directory")
        self.image_status.pack(side="bottom")

        for key in "123456789":
            self.root.bind(f"<Key-{key}>", lambda e, k=int(key): self.on_category_key(k))
        self.root.bind("<Key-s>", lambda e: self.skip())
        self.root.bind("<Key-u>", lambda e: self.undo())
        self.root.focus_set()

        if self.settings["last_dir"] and os.path.isdir(self.settings["last_dir"]):
            self.open_directory(self.settings["last_dir"])

    # -- sessions ------------------------------------------------------------
    def select_directory(self):
        chosen = filedialog.askdirectory(initialdir=self.settings["last_dir"] or os.path.expanduser("~"))
        if chosen:
            self.open_directory(chosen)

    def open_directory(self, directory: str):
        self.source_dir = directory
        if self.settings["use_subfolders"]:
            subdirs = sorted(
                (
                    d
                    for d in os.listdir(directory)
                    if os.path.isdir(os.path.join(directory, d)) and not d.startswith(".")
                ),
                key=str.lower,
            )
            self.model.categories = subdirs or list(self.settings["categories"])
        else:
            self.model.categories = list(self.settings["categories"])
        self.model.load_images(directory)
        state = settings.load_state(directory)
        cursor = state.get("cursor")
        self.model.processed = set(state.get("processed", []))
        self.model.cursor = cursor if isinstance(cursor, int) and 0 <= cursor < len(self.model.images) else 0
        self.categorizer = Categorizer(self.model, rename_pattern=self.settings["rename_pattern"])
        self._rebuild_category_buttons()
        self._refresh_status()
        self.display_image()
        self.settings["last_dir"] = directory
        settings.save_settings(self.settings)
        if self.model.finished():
            messagebox.showinfo(WINDOW_TITLE, "No more images.")

    # -- actions ---------------------------------------------------------------
    def on_category_key(self, idx: int):
        if idx <= len(self.model.categories):
            self.handle_category(self.model.categories[idx - 1])

    def handle_category(self, category: str):
        if self.categorizer is None:
            return
        try:
            self.categorizer.handle(category, self.source_dir)
        except OSError as e:
            messagebox.showerror(WINDOW_TITLE, f"Error moving image: {e}")
            return
        self._refresh_status()
        self.display_image()
        settings.save_state(self.source_dir, self._state())
        if self.model.finished():
            messagebox.showinfo(WINDOW_TITLE, "No more images.")

    def skip(self):
        if self.categorizer is None or self.model.finished():
            return
        self.categorizer.skip(self.source_dir)
        self._refresh_status()
        self.display_image()
        settings.save_state(self.source_dir, self._state())

    def undo(self):
        if self.categorizer is None:
            return
        action = self.categorizer.undo()
        if action is not None:
            self._refresh_status()
            self.display_image()
            settings.save_state(self.source_dir, self._state())

    def toggle_mode(self):
        self.model.mode = "copy" if self.model.mode == "move" else "move"
        self.mode_button.config(text=f"Mode: {self.model.mode.capitalize()} (click to toggle)")
        self.settings["mode"] = self.model.mode
        settings.save_settings(self.settings)

    def _state(self) -> dict:
        return {"cursor": self.model.cursor, "processed": sorted(self.model.processed)}

    def _refresh_status(self):
        self.image_status["text"] = f"{self.model.remaining()} images left"
        if self.categorizer is not None:
            self.undo_button.config(state="disabled" if not self.categorizer.undo_log else "normal")

    # -- categories --------------------------------------------------------------
    def _rebuild_category_buttons(self):
        for btn in self.cat_buttons.values():
            btn.destroy()
        self.cat_buttons.clear()
        enabled = "normal" if self.categorizer is not None else "disabled"
        for i, cat in enumerate(self.model.categories):
            key = str(i + 1) if i < 9 else ""
            text = f"{cat} ({key})" if key else cat
            btn = Button(self.cat_bar, text=text, state=enabled, command=lambda c=cat: self.handle_category(c))
            btn.pack(side="left", padx=2)
            self.cat_buttons[cat] = btn
        # legacy aliases from v1: only meaningful for exactly two categories
        self.root.unbind("<Key-o>")
        self.root.unbind("<Key-p>")
        if len(self.model.categories) >= 2:
            self.root.bind("<Key-o>", lambda e: self.handle_category(self.model.categories[0]))
            self.root.bind("<Key-p>", lambda e: self.handle_category(self.model.categories[1]))

    def add_category_dialog(self):
        if not self.source_dir:
            return
        name = simpledialog.askstring("Add category", "Category name:", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name or "/" in name or name.startswith(".") or name in self.model.categories:
            messagebox.showerror("Invalid", f"'{name}' is not an acceptable category name.")
            return
        self.model.categories.append(name)
        self.settings["categories"] = list(self.model.categories)
        settings.save_settings(self.settings)
        os.makedirs(os.path.join(self.source_dir, name), exist_ok=True)
        self._rebuild_category_buttons()

    # -- display -----------------------------------------------------------------
    def display_image(self):
        if self.viewer is not None:
            self.viewer.show(self.model.current())
            return
        if self.model.current() is None:
            self.photo = None
            self.image_label.configure(image="", text="No more images.")
            return
        image = Image.open(self.model.current())
        image = image.resize((int(image.size[0] * 1.75), int(image.size[1] * 1.75)))
        self.photo = ImageTk.PhotoImage(image)
        self.image_label.configure(image=self.photo)


def main():
    root = Tk()
    app = ImageCategorizerApp(root)
    root.configure(background="black")
    root.mainloop()


if __name__ == "__main__":
    main()
```

Delete `main.py`.

- [ ] **Step 2: Manual verification (display required; use `xvfb-run` over ssh)**

Run: `imagecategorizer`
1. Opens with previous directory (if it still exists) or via Select Directory dialog.
2. `1`/`2` assign per-category; clicks on the dynamically built buttons do the same.
3. `s` skips; `u` reverts a move (file back, cursor back); toggle Mode to copy → `u` deletes the copy; `o`/`p` still map to categories 1/2.
4. Close mid-session, relaunch: cursor restored, count reflects remaining.
5. "+ Add category" → new button + key; persists across restart.
6. `-- Add on invalid input (`""`, duplicate, `/`) → error dialog, nothing breaks.

- [ ] **Step 3: Full suite + lint (regression gate)**

Run: `python -m pytest -v && ruff check image_categorizer tests`
Expected: all PASS, no violations

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: dynamic categories, undo/skip/copy, session persistence"
```

---

### Task 6: viewer — fit-to-window Canvas with zoom, pan, rotate

**Files:**
- Create: `image_categorizer/viewer.py`
- Modify: `image_categorizer/app.py` — `main()` builds a `Viewer` and passes it
- Test: `tests/test_viewer.py` (pure fit math only, no display needed)

**Interfaces:**
- Consumes: `SessionModel.current() -> str | None`.
- Produces: module-level `fit_size(img_w: int, img_h: int, can_w: int, can_h: int) -> tuple[int, int]`; class `Viewer(tk.Canvas)` with:
  - `show(path: str | None)` — open + fit to window; `None` → clears and renders "No more images." text
  - `rotate()` — display-only 90° CW, zoom resets to fit
  - wheel zoom anchored at cursor, `ButtonPress-2`/`B2-Motion` pan

- [ ] **Step 1: Write failing test**

`tests/test_viewer.py`:

```python
import pytest

from image_categorizer.viewer import fit_size


def test_fit_wider_than_canvas():
    assert fit_size(4000, 1000, 800, 800) == (800, 200)


def test_fit_taller_than_canvas():
    assert fit_size(1000, 4000, 800, 800) == (200, 800)


def test_fit_upscales_small_image():
    assert fit_size(100, 50, 800, 800) == (800, 400)


def test_typical_photo_is_not_upscaled_past_fit():
    assert fit_size(1600, 1200, 1024, 768) == (1024, 768)
```

- [ ] **Step 2: Run test, verify failure**

Run: `python -m pytest tests/test_viewer.py -v`
Expected: FAIL with `ImportError: cannot import name 'fit_size'`

- [ ] **Step 3: Implement viewer.py**

`image_categorizer/viewer.py`:

```python
import tkinter as tk

from PIL import Image, ImageTk


def fit_size(img_w: int, img_h: int, can_w: int, can_h: int) -> tuple[int, int]:
    scale = min(can_w / img_w, can_h / img_h)
    return int(img_w * scale), int(img_h * scale)


class Viewer(tk.Canvas):
    """Fit-to-window triage surface: wheel zoom anchored at cursor,
    middle-drag pan, display-only 90° CW rotation."""

    def __init__(self, master, bg="black"):
        super().__init__(master, bg=bg, highlightthickness=0)
        self._pil = None
        self._rotated = None
        self._rotate_deg = 0
        self._scale = 1.0
        self._x = self._y = 0  # top-left draw position
        self._photo = None
        self.bind("<Configure>", lambda e: self.show(self._path) if self._path else None)
        self.bind("<MouseWheel>", self._zoom)        # Windows/macOS
        self.bind("<Button-4>", self._zoom)          # X11 wheel up
        self.bind("<Button-5>", self._zoom)          # X11 wheel down
        self.bind("<ButtonPress-2>", self._pan_start)
        self.bind("<B2-Motion>", self._pan_move)
        self._path = None

    # -- load ------------------------------------------------------------------
    def show(self, path):
        self._path = path
        self.delete("all")
        self._photo = None
        self._rotate_deg = 0
        if path is None:
            self._pil = None
            self.create_text(
                max(self.winfo_width() // 2, 60),
                max(self.winfo_height() // 2, 30),
                fill="white",
                text="No more images.",
            )
            return
        self._pil = Image.open(path)
        self.winfo_toplevel().after_idle(self._fit)

    # -- layout ----------------------------------------------------------------
    def _fit(self):
        if self._pil is None:
            return
        self._rotate()
        can_w = max(self.winfo_width(), 1)
        can_h = max(self.winfo_height(), 1)
        w, h = fit_size(self._rotated.width, self._rotated.height, can_w, can_h)
        self._scale = w / self._rotated.width
        self._x, self._y = (can_w - w) // 2, (can_h - h) // 2
        self._render(w, h)

    def _rotate(self):
        self._rotated = self._pil.rotate(self._rotate_deg, expand=True) if self._rotate_deg else self._pil

    def _render(self, w: int, h: int):
        self.delete("all")
        resized = self._rotated.resize((max(w, 1), max(h, 1)), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(resized)
        self.create_image(self._x, self._y, image=self._photo, anchor="nw")

    # -- zoom / pan --------------------------------------------------------------
    def _zoom(self, event):
        if self._pil is None or self._rotated is None:
            return
        factor = 1.25 if (getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0) else 0.8
        old_scale = self._scale
        self._scale = min(max(old_scale * factor, 0.01), 20.0)
        if self._scale == old_scale:
            return
        # keep the image point under the cursor fixed on screen
        ix = (event.x - self._x) / old_scale
        iy = (event.y - self._y) / old_scale
        self._x = event.x - ix * self._scale
        self._y = event.y - iy * self._scale
        self._render(int(self._rotated.width * self._scale), int(self._rotated.height * self._scale))

    def _pan_start(self, event):
        self._pan_prev = (event.x, event.y)

    def _pan_move(self, event):
        if not hasattr(self, "_pan_prev"):
            return
        dx, dy = event.x - self._pan_prev[0], event.y - self._pan_prev[1]
        self._pan_prev = (event.x, event.y)
        self.move("all", dx, dy)
        self._x += dx
        self._y += dy

    # -- rotate ------------------------------------------------------------------
    def rotate(self):
        if self._pil is None:
            return
        self._rotate_deg = (self._rotate_deg + 90) % 360
        self._fit()
```

Two fidelity notes that are allowed instead of being traps:
- Zoom re-renders the full image per scroll step — fine to ~20MP; label in code: `# shortcut: full re-render per zoom step, fine to ~20MP; switch to crop-based zoom only if real sessions hit it.` (place it above `_zoom`).
- `_scale` bounds (0.01–20) prevent runaway scroll from white-canvas thrash.

- [ ] **Step 4: Wire viewer into app**

In `image_categorizer/app.py`:

1. Add to imports: `from .viewer import Viewer`.
2. Replace bottom of file with:

```python
def main():
    root = Tk()
    root.configure(background="black")
    ImageCategorizerApp(root, viewer=Viewer(root))
    root.mainloop()


if __name__ == "__main__":
    main()
```

3. In `__init__`, add after the existing `self.root.bind("<Key-u>", ...)` line:

```python
        self.root.bind("<Key-r>", lambda e: self.viewer.rotate() if self.viewer else None)
```

No other app changes — the `viewer=None` Label fallback from Task 5 stays intact for tests/embedding.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_viewer.py -v`
Expected: 4 PASS

Manual: `imagecategorizer` — image fits window on load and on resize; wheel zooms around cursor; middle-drag pans; `r` rotates; zoom into an oversized image does not throw.

- [ ] **Step 6: Suite + lint + commit**

Run: `python -m pytest -v && ruff check image_categorizer tests`
Expected: all PASS, no violations

```bash
git add image_categorizer/viewer.py image_categorizer/app.py tests/test_viewer.py
git commit -m "feat: canvas viewer (fit, wheel zoom, pan, rotate)"
```

---

### Task 7: metadata panel

**Files:**
- Create: `image_categorizer/metadata.py`
- Modify: `image_categorizer/app.py` — `i` toggles a bottom info `Label`
- Test: `tests/test_metadata.py`

**Interfaces:**
- Produces: `describe(path: str) -> str`:
  - always-up lines: `File: <basename>`, `Format: <PIL format>`, `Dimensions: WxH`, `Size: <N> KiB`
  - EXIF lines only when present: `Make: …` (tag `0x010F`), `Model: …` (tag `0x0110`), `DateTime: …` (tag `0x0132`)
  - never raises: unreadable → `"File: <basename>\n(unreadable)"`

- [ ] **Step 1: Write failing tests**

`tests/test_metadata.py`:

```python
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
```

- [ ] **Step 2: Run test, verify failure**

Run: `python -m pytest tests/test_metadata.py -v`
Expected: FAIL with `ImportError: cannot import name 'describe'`

- [ ] **Step 3: Implement**

`image_categorizer/metadata.py`:

```python
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
```

- [ ] **Step 4: Wire into app**

In `image_categorizer/app.py`:

1. Import: `from .metadata import describe`.
2. In `__init__`, after the `self.root.bind("<Key-r>", ...)` line:

```python
        self.info_shown = False
        self.info_label = Label(self.root, justify="left", anchor="w", fg="white")
        self.root.bind("<Key-i>", lambda e: self.toggle_info())
```

(and pack it after `self.image_status.pack(...)` by moving the `_refresh_status`-adjacent line: add `self.info_label.pack(side="bottom", fill="x")` directly below the `image_status` pack so the info panel sits under the counter.)

3. New method, placed next to `toggle_mode`:

```python
    def toggle_info(self):
        if self.model.current() is None:
            return
        if self.info_shown:
            self.info_shown = False
            self.info_label["text"] = ""
        else:
            self.info_shown = True
            self.info_label["text"] = describe(self.model.current())
```

4. In `display_image`, first lines:

```python
        if self.info_shown and self.model.current() is not None:
            self.info_label["text"] = describe(self.model.current())
```

- [ ] **Step 5: Suite + lint + manual + commit**

Run: `python -m pytest -v && ruff check image_categorizer tests`
Expected: all PASS, no violations

Manual: `imagecategorizer`, press `i` → panel shows File/Format/Dimensions/Size (+ EXIF lines on camera JPEGs), `i` again hides, panel updates per image while shown.

```bash
git add image_categorizer/metadata.py image_categorizer/app.py tests/test_metadata.py
git commit -m "feat: metadata panel (format, dimensions, size, EXIF make/model/date)"
```

---

### Task 8: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: test suite, `pyproject.toml` from Task 1.
- Produces: CI gate on `main` and PRs.

- [ ] **Step 1: Write workflow**

`.github/workflows/ci.yml`:

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e .
      - run: ruff check image_categorizer tests
      - run: pytest -v
```

- [ ] **Step 2: Verify locally that the same commands pass**

Run: `pip install -e . && ruff check image_categorizer tests && pytest -v`
Expected: clean, all PASS

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: pytest + ruff across Python 3.9-3.13"
```

---

### Task 9: Release — PyPI + Windows .exe + Linux AppImage

**Files:**
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `pyproject.toml` (Task 1), tag convention `v*`.
- Prereq (manual, once): GitHub Repo Settings → Environments → create `pypi`, and configure PyPI Trusted Publishing for this repo with workflow `release.yml`, environment `pypi`. Confirm PyPI name availability before the first tag.
- Produces: PyPI upload + GitHub Release with `imagecategorizer.exe` and `ImageCategorizer-x86_64.AppImage` on every `v*` tag.

- [ ] **Step 1: Write workflow**

`.github/workflows/release.yml`:

```yaml
name: Release
on:
  push:
    tags: ["v*"]

permissions:
  contents: write
  id-token: write

jobs:
  build-wheels:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build
      - run: python -m build
      - uses: actions/upload-artifact@v4
        with:
          name: wheels
          path: dist/*

  publish-pypi:
    needs: build-wheels
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/imagecategorizer
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: wheels
          path: dist
      - uses: pypa/gh-action-pypi-publish@release/v1

  release-exe:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e . pyinstaller
      - run: pyinstaller --onefile --windowed --name imagecategorizer image_categorizer/app.py
      - uses: actions/upload-artifact@v4
        with:
          name: exe
          path: dist/imagecategorizer.exe

  release-appimage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e . pyinstaller
      - run: pyinstaller --onefile --name imagecategorizer image_categorizer/app.py
      - name: Build AppImage
        run: |
          APPDIR=imagecategorizer.AppDir
          mkdir -p "$APPDIR/usr/bin"
          cp dist/imagecategorizer "$APPDIR/usr/bin/"
          cat > "$APPDIR/imagecategorizer.desktop" <<'EOF'
          [Desktop Entry]
          Type=Application
          Name=Image Categorizer
          Exec=imagecategorizer
          Icon=imagecategorizer
          Categories=Graphics;
          EOF
          python - <<'EOF'
          from PIL import Image
          img = Image.new("RGB", (128, 128), (200, 60, 60))
          img.save("imagecategorizer.AppDir/imagecategorizer.png")
          EOF
          curl -sL -o appimagetool https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
          chmod +x appimagetool
          ./appimagetool --appimage-extract-and-run "$APPDIR" ImageCategorizer-x86_64.AppImage
      - uses: actions/upload-artifact@v4
        with:
          name: appimage
          path: ImageCategorizer-x86_64.AppImage

  github-release:
    needs: [build-wheels, release-exe, release-appimage]
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: artifacts
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            artifacts/exe/imagecategorizer.exe
            artifacts/appimage/ImageCategorizer-x86_64.AppImage
            artifacts/wheels/*
```

- [ ] **Step 2: Local release rehearsal (build only, no upload)**

Run: `pip install build && python -m build`
Expected: `dist/imagecategorizer-0.2.0.tar.gz` + `dist/*.whl`; `tar tf dist/*.tar.gz | head` lists `image_categorizer/` sources.

Run: `pyinstaller --onefile --name imagecategorizer image_categorizer/app.py && ./dist/imagecategorizer`
Expected: binary launches the app; delete `build/ dist/ *.spec` afterwards (gitignored since Task 1).

- [ ] **Step 3: Commit + tag + verify**

```bash
git add .github/workflows/release.yml
git commit -m "ci: release pipeline (PyPI trusted publish, Windows exe, Linux AppImage)"
git tag v0.2.0
git push origin main v0.2.0
```

Expected on GitHub: workflow green; GitHub Release with exe + AppImage + wheels attached; PyPI project page live.

---

### Task 10: README

**Files:**
- Modify: `README.md` (replace the two-line stub)

**Interfaces:**
- Produces: user-facing docs matching shipped behavior; the Releases link uses the exact URL from `git remote -v`.

- [ ] **Step 1: Rewrite README.md**

```markdown
# imagecategorizer

Fast single-image triage for classification datasets: open a folder,
categorize one photo at a time with the keyboard, files land in
per-category subfolders.

## Install

```bash
pip install imagecategorizer
```

No Python needed? Download the Windows `.exe` or Linux `.AppImage` from the
[Releases](<REAL-REPO-URL>/releases) page — `<REAL-REPO-URL>` is the URL of
this repository (see `git remote -v`), filled in by the executor, never left
as a placeholder in the committed file.

## Usage

Run `imagecategorizer` (or double-click the binary), click **Select
Directory**, then work the keyboard:

- **1–9** — assign the current image to category N (buttons in the toolbar do the same)
- **o / p** — legacy aliases for categories 1 and 2
- **s** — skip (leave in place, move on)
- **u** — undo last action (move reverts; copy deletes the copy)
- **i** — toggle the info panel (format, dimensions, size, EXIF make/model/date)
- **r** — rotate the display 90° clockwise (display only)

The **Mode** button toggles copy vs move; the choice persists between runs.
"+ Add category" creates a new destination folder and button instantly.

## Persistence

Progress (cursor position, processed list) is saved as
`.imagecategorizer-state.json` inside the source folder, so closing and
reopening — even on another machine via sync — resumes where you stopped.
App-wide preferences live in `~/.imagecategorizer/settings.json`.

## Development

```bash
pip install -e .
pytest
```

```

- [ ] **Step 2: Verify docs vs reality**

Read the final README start to finish; confirm every keybind (`1-9`, `o`, `p`, `s`, `u`, `i`, `r`), the Mode toggle, the state file name, and the pip command match the code in `image_categorizer/`. Fix mismatches directly in README.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: full README (install, keybinds, persistence, dev)"
```

---

## Final verification

- [ ] `python -m pytest` — full suite PASS
- [ ] `ruff check image_categorizer tests` — clean
- [ ] `pip install -e . && imagecategorizer` — manual pass across Task 5 Step 2 checklist plus viewer/info checks from Tasks 6-7
- [ ] Tag `v0.2.0` pushed → release workflow green, PyPI page live, exe + AppImage attached.

## Self-review checklist (completed while writing)

1. **Spec coverage** — Spec sections map to tasks: restructure + entry point (T1), settings/state (T2), model (T3), categorizer copy/move/undo/skip (T4), dynamic categories + keybinds + persistence (T5), fit/zoom/pan/rotate viewer (T6), metadata EXIF panel + rename (T4/T7), CI (T8), PyPI + exe + AppImage (T9), docs (T10). Categorizer's rename behavior is built into Task 4 (`rename_pattern`), so the spec's "rename-on-move" has no orphan task.
2. **Placeholders** — none: the only substitution token is `<REAL-REPO-URL>` in the README task, which ships with an explicit instruction (take from `git remote -v`) and is verified against reality in Step 2.
3. **Type consistency** — `Categorizer.handle(category, source_dir)` and `skip(source_dir)` used identically in T4 tests and T5 app code; `_settings_file` monkeypatch target used in every settings test; `describe(path)` returns str everywhere.
