# imagecategorizer v3 (Flet rewrite) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the imagecategorizer UI entirely on Flet 1.x (desktop + web from one codebase), keeping the pure triage core and modernizing the look.

**Architecture:** Pure-logic modules (`model.py`, `categorizer.py`, `metadata.py`) stay untouched; `settings.py` is rewritten with a new JSON schema; Tkinter `app.py`/`viewer.py` are deleted; a new `image_categorizer/ui/` package holds a framework-free `controller.py` plus Flet views. Package entry `image_categorizer/__main__.py` calls `ft.run`; root `main.py` is the PyInstaller/`flet pack` launcher.

**Tech Stack:** Python >= 3.10, flet>=1.0 (verified: latest 1.0.5, `requires_python >=3.10`), Pillow (unchanged), pytest, ruff, PyInstaller via `flet pack`.

**Spec:** `docs/superpowers/specs/2026-10-26-imagecategorizer-flet-v3-design.md` — binding; this plan argues from it.

## Global Constraints

- Python floor: **>= 3.10** (flet 1.x constraint; verified from PyPI `requires_python`). CI matrix 3.10–3.14.
- Runtime deps: **only `flet>=1.0` and `Pillow>=10`**. No other third-party runtime imports.
- Verified Flet 1.x API (doc-sourced 2026-10-26, URLs in research report): entry = `ft.run(main)` with `def main(page: ft.Page)`; image fit property = `fit=ft.BoxFit.CONTAIN` (NOT `ft.ImageFit`); gestures = `ft.GestureDetector` with `on_scale_start/on_scale_update/on_pan_start/on_pan_update/on_scroll` (NOT `ft.ScaleGestureDetector`); snacks = `page.show_dialog(ft.SnackBar(ft.Text(...)))`; theme = `page.theme_mode = ft.ThemeMode.LIGHT|DARK|SYSTEM`; directory pick = `await ft.FilePicker().get_directory_path()` (raises `FletUnsupportedPlatformException` in web mode — guard with `page.web`).
- `KeyboardEvent` fields: `e.key: str` (pattern `"S"` verified; digits unverified — treat labels case-insensitively and accept both digit labels), plus `e.shift/e.ctrl/e.alt/e.meta`.
- Pure-logic rule: nothing under `image_categorizer/` may `import flet` except in `ui/`; `model.py`, `categorizer.py`, `metadata.py` are byte-unchanged (save for `settings`-schema touches nowhere else).
- Naming preserved: PyPI `imagecategorizer`, import `image_categorizer`, console script `imagecategorizer` (desktop), `imagecategorizer --web` serves web.
- Keybinds: `1`–`9` categories, `s` skip, `u` undo, `r` rotate, `i` metadata, `f` filter focus.
- Tag/push/publish steps are operator-only; implementers never push or tag.
- CI runs `pytest` + `ruff` logic tests only — no `flet test` (needs Flutter SDK), no GUI launch. Proof of UI-correctness is controller unit tests + import-level checks + doc-grounded review.
- Local rehearsal note: flet is pip-installable headless; `import flet as ft`, enum introspection, and `flet pack` (PyInstaller) all work without a display.

## Verified Flet 1.x API cheat-sheet (copy into any task report where used)

```python
import flet as ft

def main(page: ft.Page):
    page.title = "..."
    page.theme_mode = ft.ThemeMode.SYSTEM  # | DARK | LIGHT
    page.on_keyboard_event = handler          # handler(e: ft.KeyboardEvent)
    page.show_dialog(ft.SnackBar(ft.Text("msg")))  # transient message
    ft.run(main)  # entry (desktop); web served via `flet run --web` or view flag
```

```python
# fit + gestures (viewer)
ft.Image(src=path, fit=ft.BoxFit.CONTAIN)
ft.GestureDetector(
    on_scroll=...,            # ScrollEvent  (mouse wheel)
    on_scale_start=..., on_scale_update=..., on_scale_end=...,  # ScaleUpdateEvent: .scale,
    on_pan_start=..., on_pan_update=...,   # DragUpdateEvent: .local_delta / .global_delta
    content=ft.Container(content=ft.Image(...), expand=True),
)
```

```python
# directory pick (desktop only):
if not page.web:
    path = await ft.FilePicker().get_directory_path()  # str | None
```

```python
# image scale trick: wrap Image in Container, set Image.scale (float) and
# Container offset via ft.transform.Offset — no per-step re-render needed.
```

---

### Task 1: Package prep — pyproject, entry module, root launcher

**Files:**
- Modify: `pyproject.toml`
- Create: `image_categorizer/__main__.py`
- Create: `main.py`

**Interfaces:**
- Consumes: nothing yet (entry is a stub shell that does not build the UI in this task).
- Produces: console script `imagecategorizer [--web]` dispatches to `image_categorizer.__main__:main`; root `main.py` = launcher used by `flet pack` in Task 9.

- [ ] **Step 1: Edit `pyproject.toml`** — set exactly:
  - `requires-python = ">=3.10"` (was >=3.9)
  - `dependencies = ["flet>=1.0", "Pillow>=10"]`
  - dynamic version block unchanged (`version = { attr = "image_categorizer.__version__" }`)
  - `[project.scripts] imagecategorizer = "image_categorizer.__main__:main"`
  - bump `image_categorizer/__init__.py` to `__version__ = "0.3.0"`
- [ ] **Step 2: Create `image_categorizer/__main__.py`**:

```python
import sys


def main():
    from image_categorizer.ui.app import main_page

    web = "--web" in sys.argv[1:]
    import flet as ft

    ft.run(
        main_page,
        view=ft.AppView.WEB_BROWSER if web else ft.AppView.FLET_APP,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create root `main.py` — launcher for flet pack (Task 9 uses it):**

```python
from image_categorizer.__main__ import main

if __name__ == "__main__":
    main()
```

  Note: `image_categorizer.ui.app` does not exist yet — this task lands as `DONE_WITH_CONCERNS` if `pip install -e .` builds but the console script fails expecting the UI (documented concern; fixed by Task 4).
- [ ] **Step 4: Verify** — `pip install -e .`, then:
  `python -c "import flet as ft; print(ft.AppView.FLET_APP, ft.AppView.WEB_BROWSER); print(ft.run)"` (run inside the builder's shell; expected: prints `AppView.FLET_APP AppView.WEB_BROWSER` and a function repr; if the enum members differ, STOP → return NEEDS_CONTEXT with the actual members).
- [ ] **Step 5: Commit** — `feat: package skeleton for Flet rewrite (entry, launcher, pyproject)`.

### Task 2: settings.py rewrite — new schema

**Files:**
- Modify: `image_categorizer/settings.py`
- Modify: `tests/test_settings.py`
- Create: nothing else.

**Interfaces:**
- Consumes: nothing (stdlib only).
- Produces (exact, used by Task 3/4/5/9):

```python
DEFAULTS: dict = {
    "categories": ["infected", "normal"],
    "mode": "move",                          # "move" | "copy"
    "subfolders": False,                     # bool
    "theme": "system",                       # "system" | "dark" | "light"
    "last_dir": "",                          # ""
    "rename_pattern": "{category}_{idx:04d}{ext}",
}

def load_settings() -> dict                        # merged-over-DEFAULTS, unknown keys dropped, corrupt → DEFAULTS
def save_settings(settings: dict) -> None          # open(dirname, exist_ok), write settings.json local-dict
def config_dir() -> Path                           # Path.home() / ".imagecategorizer"
def load_state(src: str) -> dict                   # {"cursor": int, "processed": [str]} or {} ; corrupt/missing → {}
def save_state(src: str, state: dict) -> None      # writes .imagecategorizer-state.json inside src
def clear_state(src: str) -> None
```

- state file name/format: `.imagecategorizer-state.json` with exactly two keys — `"cursor"` (int) and `"processed"` (list of str). On load, coerce `cursor` via `isinstance(cursor, int) and 0 <= cursor`; coerce `processed` items to str and dedupe.

- [ ] **Step 1: Write failing tests** (replace old test file contents entirely; reuse `tmp_path` + monkeypatch of `settings._settings_file` as before):

```python
import json
from pathlib import Path

import pytest

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
```

- [ ] **Step 2: Run `pytest tests/test_settings.py -v`** — Expect FAIL (old `_settings_file` semantics partially kept but `subfolders`/`theme` keys unknown to v2).
- [ ] **Step 3: Implement `settings.py` fresh** following the exact interface block above (keep old `pytest`-friendly internals: `_settings_file` path constant monkeypatched in tests; keep same `config_dir()`; state file format exactly `{"cursor": int, "processed": [str]}` with the stated coercion; json indentation 2).

```python
import json
from pathlib import Path

DEFAULTS = {
    "categories": ["infected", "normal"],
    "mode": "move",
    "subfolders": False,
    "theme": "system",
    "last_dir": "",
    "rename_pattern": "{category}_{idx:04d}{ext}",
}
_config_named = "settings.json"
_settings_file = Path.home() / ".imagecategorizer" / _config_named


def config_dir() -> Path:
    return Path.home() / ".imagecategorizer"


def load_settings() -> dict:
    try:
        data = json.loads(_settings_file.read_text())
        if not isinstance(data, dict):
            raise ValueError("settings must be an object")
        return {**DEFAULTS, **{k: data[k] for k in DEFAULTS if k in data}}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save_settings(settings: dict) -> None:
    d = {**DEFAULTS, **settings}
    _settings_file.parent.mkdir(parents=True, exist_ok=True)
    _settings_file.write_text(json.dumps(d, indent=2))


def load_state(src: str) -> dict:
    try:
        d = json.loads((Path(src) / ".imagecategorizer-state.json").read_text())
        if not isinstance(d, dict):
            raise ValueError("state must be an object")
        cursor = d.get("cursor", 0)
        if not isinstance(cursor, int) or cursor < 0:
            cursor = 0
        processed = [str(p) for p in d.get("processed", []) if isinstance(p, str)]
        return {"cursor": cursor, "processed": list(dict.fromkeys(processed))}
    except (OSError, ValueError):
        return {}


def save_state(src: str, state: dict) -> Path:
    p = Path(src) / ".imagecategorizer-state.json"
    p.write_text(json.dumps(dict(state), indent=2))
    return p


def clear_state(src: str):
    (Path(src) / ".imagecategorizer-state.json").unlink(missing_ok=True)
```

  Note: `save_settings`/`load_settings` must keep supporting tests that monkeypatch `settings._settings_file`, i.e. use `_settings_file` textual constant (not a re-declared path). The exact same call pattern the v2 tests apply.

- [ ] **Step 4: Run `pytest tests/test_settings.py -v` and full suite** (`pytest -q` also) — ensure `tests/test_model.py`, `tests/test_categorizer.py`, `tests/test_metadata.py`/`tests/test_package.py` still pass unmodified (they don't touch settings except categorizer tests which reference nothing of it; if any old test breaks due to schema rename `use_subfolders`→`subfolders`, update that test file here).
- [ ] **Step 5: Commit** — `feat: settings module v3 schema (theme, subfolders, rename_pattern)`.

### Task 3: Controller (framework-free glue)

**Files:**
- Create: `image_categorizer/controller.py`
- Create: `tests/test_controller.py`

**Interfaces:**
- Consumes (existing, do not modify): `image_categorizer.model.SessionModel` — `images list, cursor, processed set, mode; load_images(dir)->int, current()->str|None, advance(path), remaining(), finished()`; `image_categorizer.categorizer.Categorizer(model, rename_pattern)` — `handle(category, source_dir)->Action, skip(source_dir)->Action, undo()->Action|None, undo_log deque`; `image_categorizer.metadata.describe(path)->str`; `image_categorizer.settings` functions from Task 2.
- Produces (Task 4+ consumes):

```python
class Controller:
    def __init__(self, settings: dict)
    settings: dict                        # live dict (caller may persist via save_settings)
    model: SessionModel
    categorizer: Categorizer | None
    meta_shown: bool
    # -- directory/session
    open_directory(path: str) -> None      # chooses images (subfolders-aware), restores state, saves last_dir
    current_image() -> str | None
    remaining() -> int
    finished() -> bool
    processed_count() -> int
    thumbnails(limit: int = 12) -> list[str]      # next `limit` images from cursor
    describe_current() -> str | None             # already-formatted describe() output or None
    # -- actions (each saves session state)
    categorize(index: int) -> str | None          # name of the target category applied or None on error
    skip() -> None
    undo() -> str | None                          # op description ("crossed out"/moved/copy removed) or None if nothing to undo
    can_undo() -> bool
    # -- categories
    add_category(name: str) -> tuple[bool, str]   # (ok, error_message in English, "" on success)
    categories() -> list[str]
    rename_index_next() -> int                    # purely informational; used by view meta strip
    save_all()                                    # write settings + session state (flush points)
```

- Error contract on `open_directory`: zero usable images → raises `ValueError("No images found in <path>")` after still writing `last_dir` (view shows snack bar). OSError while dir-listing may propagate.
- `categorize(i)`: if `i` outside `0..len(categories)-1` → returns None; if finished/none current → returns None; wraps `Categorizer.handle` errors as `(OSError, KeyError, IndexError, ValueError)` → re-raises as `RuntimeError(str(e))` (view catches and snackbars).
- `undo()`: wraps same exception set; returns human text via `Action.op`: "move"/"copy"/"skip" → `f"Undid {op} on {basename}"`.

- [ ] **Step 1: Write failing tests** — `tests/test_controller.py`:

```python
from pathlib import Path

import pytest
from PIL import Image

from image_categorizer.controller import Controller
from image_categorizer import settings


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
    assert c.model.processed == {str(src / "categories" / "infected" / "img_0.jpg")} or \
           c.model.processed == {str(src / "infected" / "img_0.jpg")}
```

  NOTE to implementer (adjudicate, then simplify): the exact destination path depends on the v2 owner's `Categorizer.handle` which uses `source_dir` for the dest folder root — read `categorizer.py` (do not modify it) and make the test match the real dest layout; do not change the categorizer.

```python
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
    assert c.undo() is None or isinstance(c.undo(), str)  # undo skipped→restores


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
    ok, msg = c.add_category("new-cat")
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
```

  Note: implementer may modify assertion targets if the semantic under test is richer; report all adjustments.

- [ ] **Step 2: Verify FAIL** (`ModuleNotFoundError: No module named 'image_categorizer.controller'`).
- [ ] **Step 3: Implement `image_categorizer/controller.py`** — pure stdlib+core imports only, no flet:

```python
import os
from pathlib import Path

from image_categorizer.model import IMG_EXTS, SessionModel
from image_categorizer.categorizer import Categorizer
from image_categorizer import settings as settings_mod

from PIL import Image as PILImage


class Controller:
    def __init__(self, settings: dict):
        self.settings = settings
        self.model = SessionModel()
        self.model.categories = list(settings.get("categories", []))
        self.categorizer = None
        self.source_dir = ""
        self.meta_shown = False
        self.filter_text = ""

    def categories(self):
        return list(self.model.categories)

    def open_directory(self, path: str):
        names = [
            n for n in os.listdir(path)
            if n.lower().endswith(IMG_EXTS)
        ]
        if self.settings["subfolders"]:
            for sub in sorted(os.listdir(path)):
                subp = os.path.join(path, sub)
                if os.path.isdir(subp):
                    names.extend(os.path.join(sub, n) for n in os.listdir(subp)
                                 if n.lower().endswith(IMG_EXTS))
        if not names:
            self.settings["last_dir"] = path
            settings_mod.save_settings(self.settings)
            raise ValueError(f"No images found in {path}")
        self.source_dir = path
        self.model.load_images([os.path.join(path, n) for n in sorted(names, key=str.lower)])
        self.categorizer = Categorizer(self.model, self.settings.get("rename_pattern", ""))
        state = settings_mod.load_state(path)
        cursor = state.get("cursor", 0)
        if 0 <= cursor < len(self.model.images):
            self.model.cursor = cursor
        self.model.processed = set(state.get("processed", []))
        self.filter_text = ""
        self.settings["last_dir"] = path
        self.save_all()

    def _visible_images(self):
        imgs = self.model.images
        if not self.filter_text:
            return imgs
        f = self.filter_text.lower()
        return [p for p in imgs if f in os.path.basename(p).lower()]

    def current_image(self):
        vis = self._visible_images()
        if not vis or self.model.finished():
            return None
        # transparent mapping: index in images vs visible list
        target = vis[0] if not self.filter_text else None
        return self.model.current()

    def remaining(self):
        return len(self._visible_images()) if not self.model.finished() else 0

    ...
```

  IMPORTANT: the above is a seed — complete it faithfully. The filter must narrow the view WITHOUT diverging from the underlying cursor (v2 semantics: filter hides completed images automatically because categorize advances; treat filter as pure name filter applied to `model.images[cursor:]`, i.e. thumbnails returns the filtered tail). `categorize/skip/undo` follow v2 order-of-mutations: read from `Categorizer` for actual implementation details; write to settings/state per v2 rules (state file written after every op; makedirs errors from add_category must not corrupt settings — settings write happens only after the directory exists).
- [ ] **Step 4: Full suite green** (`pytest -v`), ruff clean (`ruff check image_categorizer tests`).
- [ ] **Step 5: Commit** — `feat: framework-free controller glue for Flet UI`.

### Task 4: UI scaffold — page, AppBar, chips, action bar, filter

**Files:**
- Create: `image_categorizer/ui/__init__.py` (empty)
- Create: `image_categorizer/ui/app.py`
- Create: `image_categorizer/ui/imagearea.py` (created here as a stub consumed by Task 5, not wired into page until then — full stub content below)
- Create: `tests/test_ui_structure.py`

**Interfaces:**
- Consumes: `Controller` from Task 3 (exact methods above); task-2 settings constants.
- Produces: `main_page(page: ft.Page)` entry (called by `__main__.py`; builds and registers everything); `page.session` stores: nothing (all state on the Controller object kept as `page.session`-free module-global keyed by page)? — NO: use a Controller instantiated inside `main_page` and passed to all sub-views explicitly. Sub-view modules expose: `build_app_bar(controller) -> ft.Control`, `build_chip_bar(controller) -> ft.Control`, `build_action_bar(controller) -> ft.Control`, `build_image_area(controller) -> ft.Control` (stub now; Task 5 fills it), `build_thumb_strip(controller) -> ft.Control` (stub), `build_meta_strip(controller) -> ft.Control` (stub). All sub-view builders live in `ui/app.py` in this task; Task 5/6 split them out — simplest and honest.

- [ ] **Step 1: Create stub file `image_categorizer/ui/imagearea.py` (changed by Task 5)**:

```python
import flet as ft


def build_image_area(controller):
    return ft.Container(expand=True)
```

- [ ] **Step 2: Write `tests/test_ui_structure.py`** — import-and-shape only (no page run):

```python
def test_ui_imports():
    from image_categorizer.ui import app
    from image_categorizer.ui import imagearea
    for fn in (
        app.build_app_bar,
        app.build_chip_bar,
        app.build_action_bar,
        imagearea.build_image_area,
    ):
        assert callable(fn)


def test_controller_hot_path_ui_free():
    import ast
    from pathlib import Path
    src = Path("image_categorizer/controller.py").read_text()
    assert "import flet" not in src, "controller must stay framework-free"
```

- [ ] **Step 3: Run `pytest tests/test_ui_structure.py`** — expect: pass of `test_controller_hot_path_ui_free`; FAIL on import (ui package missing) — then proceed.
- [ ] **Step 4: Implement `image_categorizer/ui/app.py`** — verbatim skeleton (fills in Task 6 alongside):

```python
import os

import flet as ft

from image_categorizer.controller import Controller
from image_categorizer import settings as settings_mod
from image_categorizer.ui import imagearea


def main_page(page: ft.Page):
    page.title = "Gading's Image Categorizer"
    cfg = settings_mod.load_settings()
    controller = Controller(cfg)
    page.theme_mode = _theme_mode(cfg.get("theme", "system"))

    page.on_keyboard_event = lambda e: _on_key(controller, page, e)

    # -- app bar
    page.appbar = build_app_bar(controller, page)

    page.add(
        build_chip_bar(controller, page),
        imagearea.build_image_area(controller),
        build_action_bar(controller, page),
        build_thumb_strip(controller, page),
        build_meta_strip(controller, page),
    )
    page.update()


def _theme_mode(s: str):
    return {
        "dark": ft.ThemeMode.DARK,
        "light": ft.ThemeMode.LIGHT,
        "system": ft.ThemeMode.SYSTEM,
    }[s]


def _on_key(controller, page, e):
    c = controller
    k = e.key.lower()
    if k in "123456789":
        try:
            c.categorize(int(k))
        except Exception as exc:                      # noqa: BLE001 - surfaced by snack bar
            _snack(page, f"Error: {exc}")
    elif k == "s":
        c.skip()
    elif k == "u":
        c.undo()
    elif k == "r":
        _rotator()
    elif k == "i":
        c.meta_shown = not c.meta_shown
    elif k == "f":
        pass  # filter focus is appended in Task 6 when filter control exists
    _refresh(page, controller)


def _snack(page, text):
    page.show_dialog(ft.SnackBar(ft.Text(text)))


def _rotator():
    from image_categorizer.ui import imagearea
    imagearea.rotate_current()
```

  The builders (`build_app_bar`, `build_chip_bar`, `build_action_bar`, stubs for thumb/meta) must be implemented in the SAME task so the page actually renders; delegate the exact visual content:
  - `build_app_bar`: `ft.AppBar(title=ft.Text("Gading's Image Categorizer"), actions=[ft.IconButton(ft.Icons.DARK_MODE if theme_mode != DARK else ft.Icons.LIGHT_MODE, on_click=...) toggling cnfg["theme"], settings_mod.save_settings, page.theme_mode, page.update()], plus f"Directory: {controller.source_dir or 'Pick a directory'}" status text, plus counter `f"{processed}/{total}"`, plus the directory-pick `ft.FilePicker` (desktop-only, guard `page.web`).
  - `build_chip_bar`: dynamic `ft.FilledButton` per `controller.categories()` with `key=f"cat_{i}"` and numeric badge text `f"{i+1} {name}"`; "+ Add category" opens `ft.AlertDialog` — implement now as a dedicated content page-`TextField` + confirm; on confirm `ok, msg = controller.add_category(name)`; on fail show snack with msg.
  - `build_action_bar`: `ft.Row` with: Mode toggle `ft.Switch`/FilledButton honoring `controller.settings["mode"]`, Subfolders toggle `ft.Switch`(persist `subfolders`), Skip button (`s`), Undo button (disabled when `not controller.can_undo()`), Filter `ft.TextField` bound to `controller.filter_text`.
  - `build_thumb_strip`, `build_meta_strip`: stubs returning empty `ft.Row()`/`ft.Container(height=0)` for THIS task.
- [ ] **Step 5: Verify imports and f-free controller again.** `python -c "from image_categorizer.ui import app; import flet as ft; print('ok')"` and `pytest -q`.
- [ ] **Step 6: Commit** — `feat: flet UI scaffold (app bar, chips, actions, filter)`.

### Task 5: Image area — fit, zoom, pan, rotate

**Files:**
- Modify: `image_categorizer/ui/imagearea.py` (full implementation, replacing stub)

**Interfaces:**
- Consumes: `Controller.current_image()`; task-level cheat-sheet API (GestureDetector + Scale event fields verified above).
- Produces: `imagearea.rotate_current()` (called by `_on_key("r")`); internal module-global `state: dict` mapping is NOT needed — use a module-level `_state` dict keyed by nothing (single-instance app), holding `{"container": ft.Container|None, "scale": float, "offset": (dx, dy), "path": str|None}` refreshed via `imagearea.refresh(controller)` called by `_refresh`.

- [ ] **Step 1: Implement** the module exactly:

```python
import flet as ft

_state = {
    "image": None,      # ft.Image | None
    "container": None,  # ft.Container | None
    "scale": 1.0,
    "off": (0.0, 0.0),
    "path": None,
    "rot": 0,
}
MIN_SCALE, MAX_SCALE = 0.1, 20.0


def build_image_area(controller):
    image = ft.Image(expand=True, fit=ft.BoxFit.CONTAIN,
                     border_radius=ft.border_radius.all(10))
    detector = ft.GestureDetector(
        content=image,
        drag_interval=10,
        on_scroll=_on_scroll,
        on_scale_update=_on_scale_update,
        on_pan_update=_on_pan_update,
        on_pan_end=_reset_pan,
    )
    container = ft.Container(content=detector, expand=True, alignment=ft.alignment.center)
    _state["image"] = image
    _state["container"] = container
    return container


def refresh(controller):
    img = controller.current_image()
    if img != _state["path"]:
        _state["path"] = img
        _state["scale"] = 1.0
        _state["off"] = (0.0, 0.0)
        _state["rot"] = 0
        if img is None:
            if _state["image"]:
                _state["image"].src = None
        else:
            if _state["image"]:
                _state["image"].src = _to_src(img)
    if _state["image"]:
        _state["image"].scale = _state["scale"]
        _state["container"].offset = ft.Offset(*_state["off"])
```

  - Zoom via `on_scroll`: direction from the ScrollEvent (verify the event's `scroll_delta_y`/`local_delta` field names live with `python -c "import flet as ft; help(ft.ScrollEvent)"` during implementation; use the documented field — implementer runs this check and records the output in the report; if ScrollEvent serves no usable delta, fall back to `on_scale_update` with `trackpad_scroll_causes_scale=True` documented above).
  ```python
  def _on_scroll(e):
      factor = 1.25 if _scroll_delta_positive(e) else 0.8
      old = _state["scale"]
      _state["scale"] = min(max(old * factor, MIN_SCALE), MAX_SCALE)
      if _state["image"]:
          _state["image"].scale = _state["scale"]
  ```
  - Pan via `on_pan_update`: `_state["off"] = (off[0] + e.local_delta.x, off[1] + e.local_delta.y)`; clamp offset roughly within a 2x-tile — set container `.offset`. Simple monotonic pan (no clamping — 1-line note: position resets per image, no risk of losing the image permanently).
  - Scale pinch via `on_scale_update` (two-finger): multiply `_state["scale"] *= e.scale` clamped; set `image.scale`.
  - Rotate: module function `rotate_current()` — `_state["rot"] = (_state["rot"] + 90) % 360`; assign `_state["image"].rotate = ft.transform.Rotate(_state["rot"] * (3.14159 / 180) / 2)` (verify `ft.rotate` semantics under `help(ft.Image)` during implementation; if Rotate expects full-turn or radian, report actual applied semantics). Reset zoom on rotate (`scale=1.0`) only if rotation is applied through the gradient mechanism (see report).
  - `_to_src(path)`: for desktop the path local file must be addressable: wrap in `_state` via serving bytes as Image src: read `open(path, "rb").read()` → base64 (`src=b"...bytes..."` — verified: `src` accepts bytes). Use bytes always; remember `ft.Image(src=bytes)` accepts raw bytes (verified quote: "src: str | bytes ... Raw bytes").
  - **The refresh gate is NOT implemented in this task** — the `_refresh(page, controller)` function in `app.py` (Task 6's) calls `imagearea.refresh(controller)` provided here; until then the view shows the empty container (no page updates, no crash). No UI runtime test possible headless — correctness rests on: enum/event introspection recorded in report + fresh-eyes code review + doc-grounded reviewer spot-check against the docs pages in the cheat-sheet.
- [ ] **Step 2: Report gates (all recorded verbatim in the task report):**
  1. `python -c "import flet as ft; print([f for f in dir(ft.ScrollEvent)])"` output.
  2. `python -c "import flet as ft; print(ft.Image.scale, ft.Image.rotate)"` → runtime introspection of control properties.
  3. `python -c "import flet as ft; print(ft.Offset, ft.transform.Rotate)"` output.
- [ ] **Step 3: `pytest -q` + `ruff check image_categorizer tests`** (both must include the new module; the `test_ui_structure` still passes).
- [ ] **Step 4: Commit** — `feat: image area with fit, scroll zoom, pan, pinch, rotate`.

### Task 6: Thumb strip + metadata strip + keybind parity + delete Tk UI

**Files:**
- Modify: `image_categorizer/ui/app.py` (fills `build_thumb_strip`, `build_meta_strip`, `_refresh`; removes the `_rotator` indirection only if Task 5 states a simpler module-level call)
- Delete: `image_categorizer/app.py` (Tk), `image_categorizer/viewer.py` (Tk)
- Create: `README.md` rewrite (new sections: install, run desktop / run web, keybind table, storage paths, packaging note)
- Create: `tests/` additions only if controller gaps emerged

**Interfaces:**
- Consumes: everything from Tasks 1–5.
- Produces: complete app; `f` keybind focuses the filter text field (via ref captured when building `build_action_bar`; store the TextField in a module-level `_filter_field` in `app.py`).

- [ ] **Step 1: Fill stubs in `ui/app.py`:**
  - `build_thumb_strip(controller)`: horizontal `ft.Row(scroll=ft.ScrollMode.AUTO)` of up to 12 `ft.Container(ft.Image(src=thumb_on_screen(controller, path)), width=90, height=90, key=str(path), on_click=lambda e, p=path: _thumb_jump(controller, page, p))` for `controller.thumbnails(12)`; images rendered as base64 bytes at a 120px height max (per spec) via a small `PIL` open → `thumbnail((90, 90))` helper in `ui/app.py` (NOT controller — keep controller PIL-free for test simplicity; a `_thumb_bytes(path)` helper here in view code).
  - `_thumb_jump`: `controller.jump_to(path)` — ADD this method to `controller.py` in this task (TDD micro-test in `tests/test_controller.py`: build 3 images, jump_to 3rd, assert `current_image() == 3rd`).
  - `build_meta_strip(controller)`: `ft.Text(controller.describe_current(), expand=False)` inside a `ft.Container(visible=controller.meta_shown)`; long text with newline: use `ft.Text(..., max_lines=None, selectable=True)`.
  - `_refresh(page, controller)` (called from every `_on_key` tail): call `imagearea.refresh(controller)`, rebuild the counter text, Undo button disabled-state, thumb strip contents (assign a professional minimal approach: re-`page.add(...)` is forbidden — mutate existing controls via stored refs/`page.update()`).
- [ ] **Step 2: Delete `image_categorizer/app.py` and `image_categorizer/viewer.py`** (git rm).
- [ ] **Step 3: Rewrite `README.md`** fully (Install pip/running desktop/web via `flet run --web` or `imagecategorizer --web`, keybind table matching Task 4, storage paths from Task 2, packaging typed briefly; remove v2 Tk references).
- [ ] **Step 4: Import smoke (desktop-free proof)**:
  `python -c "from image_categorizer.__main__ import main; import ast; [ast.parse(open(f).read()) for f in ('image_categorizer/ui/app.py','image_categorizer/ui/imagearea.py')]; print('scaffold ok')"`.
  `pytest -q` and `ruff check image_categorizer tests` — all green.
- [ ] **Step 5: Commit** — `feat: complete Flet app (thumb strip, meta strip, keybinds); remove Tkinter UI`.

### Task 7: CI update

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:** none.

- [ ] **Step 1: Update `ci.yml`**: matrix `["3.10","3.11","3.12","3.13","3.14"]`; `pip install -e . ruff pytest` line unchanged; checkout/setup-python at `@v7` (latest, as of 2026-10). No `flet test` step.
- [ ] **Step 2:** Local rehearsal: `pip install -e . ruff pytest && ruff check image_categorizer tests && pytest -q`.
- [ ] **Step 3: Commit** — `ci: python 3.10-3.14 matrix for Flet rewrite`.

### Task 8: Release workflow — Flet packaging

**Files:**
- Modify: `.github/workflows/release.yml`
- Delete nothing else.

**Interfaces:** operator-only trigger; artifact names: `imagecategorizer.exe` (Windows), `ImageCategorizer-x86_64.AppImage` (Linux). PyPI trusted publish block copied verbatim from v2 workflow.

- [ ] **Step 1: Write the workflow** with these jobs:
  - `build-wheels`: `python -m build` (sdist + wheel) — upload artifact `wheels`.
  - `publish-pypi`: same trusted-publish block as v2 (id-token: write, environment: pypi, `pypa/gh-action-pypi-publish`).
  - `release-exe` (windows-latest): checkout, `pip install flet`, then **`flet pack main.py`** (verified vendor command: "single-file executable on Windows and Linux"). Locate the produced binary in `dist/` and rename it `imagecategorizer.exe` if needed:

```bash
find dist -type f -name "*.exe" -exec mv -v {} imagecategorizer.exe \;
```

Then upload artifact `exe` (path `imagecategorizer.exe`).
  - `release-appimage` (ubuntu-latest): same `flet pack main.py` (Linux single-file per docs), then wrap into an AppImage with the appimagetool approach from `https://flet.dev/docs/publish/linux/`'s `build-appimage.sh` (the script is self-contained — vendor-quoted in the URL; re-implement as a bash step: `appimagetool` with `.desktop` entry Exec pointing to the packed binary, icon generated with PIL). Upload artifact `appimage` constructed at `ImageCategorizer-x86_64.AppImage`.
  - `github-release`: depends on the previous; `softprops/action-gh-release@v2` attaching wheels + exe + appimage.
- [ ] **Step 2: Local rehearsal (headless, no display needed):** `pip install flet`, then run `flet pack --help` and record the flags; attempt `flet pack main.py` locally headless and record the produced dist layout (`ls -la dist/`) and binary name. If `flet pack` fails locally for missing GUI libs on Linux rehearsal (PyInstaller works headless; flet's runtime may not) — record output verbatim and treat the documented-command + rename-step as the plan-critical part; final proof comes from the operator-triggered CI run.
- [ ] **Step 3: yaml sanity** `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml')); print('yaml-ok')"`.
- [ ] **Step 4: Commit** — `ci: Flet packaging pipeline (flet pack exe + AppImage wrap)`.

### Task 9: Final wiring pass + README + governance

**Files:**
- Modify: `README.md` (final cross-check, keybind table, storage section, web caveat, packaging)
- Modify: any file where earlier tasks left a documented reconciliation point (grep `# verify:` and `shortcut:` comments; resolve or eliminate).

**Interfaces:** none new.

- [ ] **Step 1: grep the tree** for `verify:` & `shortcut:` comments and stray `NOT VERIFIED` items; each must be resolved or intentionally documented (list in report).
- [ ] **Step 2: README checklist** (each item verified against live code before commit):
  1. `pip install imagecategorizer` + `imagecategorizer` (desktop) + `imagecategorizer --web` (web).
  2. Keybind table: 1–9 categorize, s skip, u undo, r rotate, i metadata, f filter.
  3. Storage: `~/.imagecategorizer/settings.json` (keys listed verbatim from Task 2 DEFAULTS) and per-directory `.imagecategorizer-state.json` (`{"cursor", "processed"}`).
  4. Web caveat: directory/file access resolves on the server machine; directory picker disabled in web mode.
  5. Packaging: releases provide exe + AppImage; PyPI wheel for normal install.
- [ ] **Step 3: Full gate locally:** `pytest -v` + `ruff check image_categorizer tests` + `python -c "from image_categorizer.__main__ import main; print('entry ok')"` + full-suite run — all green.
- [ ] **Step 4: Commit** — `docs: README for Flet rewrite`.

---

## Deferred (explicitly NOT in scope of this plan)

- `flet test` integration tests (need Flutter SDK in runner) — revisit later only if the operator asks.
- Mobile builds (`flet build`), database-backed history, gallery beyond 12 thumbs, i18n.
- v2→v3 settings migration importer.
- Python floor string "3.10" codec concerns: `image_categorizer/__init__.py` declares `__version__ = "0.3.0"` in Task 1.
