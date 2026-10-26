# imagecategorizer v2 — Design

Date: 2026-10-26
Status: Approved via conversation, pending written review.

## Goal

Turn the single-file Tkinter image triage app into a full-featured,
pip-installable package, published to PyPI, with prebuilt Windows `.exe`
and Linux AppImage releases for users without Python.

## Current state

Single file `main.py` (~106 lines): pick a folder, image displays fixed
1.75x zoom, `o`/`p` keys or buttons move it into hard-coded
`infected`/`normal`. Copy code paths are dead; no persistence; no tests;
no packaging.

## Decisions

- **GUI toolkit: stay on Tkinter.** Canvas-based viewer for zoom/pan.
  Zero new GUI dependencies; Pillow is the only third-party dep. Keeps
  the `.exe` small (~30MB) and the AppImage lean.
- **Threading model: single-threaded.** A triage session is inherently
  one-image-at-a-time; no async complexity.

## Package layout

```
pyproject.toml            # setuptools; deps: Pillow; entry point
                          #   imagecategorizer = image_categorizer.app:main
image_categorizer/
├── __init__.py           # version
├── app.py                # Tk root, main(); wires panels to model
├── viewer.py             # Canvas viewer
├── model.py              # SessionModel: categories, image list, cursor, processed set
├── categorizer.py        # copy/move/skip/undo file ops (pure, no Tk)
├── metadata.py           # EXIF/format/dimensions extraction (PIL)
└── settings.py           # JSON settings load/save
tests/                    # pytest for model, categorizer, settings (tmp_path based)
.github/workflows/ci.yml      # test + lint
.github/workflows/release.yml # tag → PyPI publish + artifacts
```

Module boundaries: `model`, `categorizer`, `settings`, `metadata` know
nothing about Tk; GUI modules are thin wiring. This keeps GUI untestable
logic to a minimum and lets pytest cover the rest.

## Features

1. **Custom categories.** Category list editable in a dialog; buttons
   and keybinds (`1`..`9`) generated dynamically. Invalid input
   rejected. Stored per-project in settings.
2. **Subfolder categories.** "Use subfolders" toggle: destination
   subfolder listing becomes the category set for the session; created
   if missing, same as current behavior for `infected`/`normal`.
3. **Fix + polish existing.**
   - Copy and move unified into one file-op path behind a copy/move
     toggle (removes the dead `copy_to_*` code and the commented-out
     state).
   - Undo last action (`u`): move reverts (file back, cursor back);
     copy removes the copied file; bounded log (last 50).
   - Skip (`s`): advance cursor without moving.
   - Rotate (`r`): rotate displayed image 90° CW (display only).
   - Status counter valid for copy mode too (processed count instead of
     remaining assumptions).
4. **Better viewer.** Fit-to-window default; mouse-wheel zoom centered
   on cursor; middle-drag pan; handles huge images (no fixed 1.75x
   scale). Kept in `viewer.py`, ~100 lines of Canvas code.
5. **Session persistence.** `settings.json` stores: last source
   directory, category list, copy/move mode, viewer prefs. Per-project
   resume state (cursor position + processed files) is stored as
   `.imagecategorizer-state.json` inside the source directory itself, so
   it travels with the project over network drives or sync tools.
6. **Batch/metadata.** Panel toggled with `i`: EXIF summary, format,
   dimensions, file size. Optional rename-on-move with pattern
   `{category}_{index}{ext}` enabled per session. Multi-select is
   intentionally excluded: a triage tool is single-image by nature.

## Packaging

- **PyPI**: `pyproject.toml`, version in `__init__.py`, tag `v0.2.0` →
  trusted-publishing workflow (`pypa/gh-action-pypi-publish`).
- **.exe**: GitHub Actions runner + PyInstaller onefile; artifact
  attached to the GitHub Release.
- **AppImage**: PyInstaller onefile on ubuntu runner, wrapped via
  appimagetool; artifact attached to the Release.
- One `release.yml` builds all three on version tags.

## Testing

- pytest: `model` (cursor, undo log, processed set), `categorizer` (copy
  / move / undo on `tmp_path`), `settings` (round-trip). No Tk needed.
- GUI modules stay thin; viewer gets an offscreen smoke test skipped
  when no display available.

## Phasing (implementation order)

1. Restructure into package + entry point; app behaves exactly as now.
2. Core features (model, categorizer, settings) + tests; swap file ops.
3. Viewer replacement.
4. Metadata panel + rename-on-move.
5. Packaging, CI/release workflows, README update.

Each phase leaves the app runnable and tests green.
