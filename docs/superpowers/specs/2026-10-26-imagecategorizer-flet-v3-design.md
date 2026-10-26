# imagecategorizer v3 — Flet rewrite (design)

Date: 2026-10-26
Status: approved in chat, pending user spec review
Supersedes the Tkinter UI layer; the GUI-framework constraint ("Tkinter only") from the v2 spec is retired by user decision.

## Goal

Rewrite the app fully on the Flet framework (1.0.x, Python >= 3.10): same core triage workflow, 100% replaced UI, with a modern Material 3 look and light extras. Ship as one codebase that runs as a desktop app and as a self-hosted web app.

## Scope decisions (user-confirmed)

- Full revamp, open scope with restraint taken: modern look + a few light extras only.
- Targets: desktop + web (`flet` app + `--web` web serve). No mobile builds.
- Storage format is free to redesign; backward compatibility with v2 settings/state files is NOT required.
- The Tkinter app is removed entirely — one app, no legacy fallback.
- Core feature set carries over: directory selection (top level), optional subfolder enumeration, custom categories (add UI + folders created), copy/move mode toggle, skip, undo, sequential rename via pattern, metadata panel, image viewer with zoom/rotate, keyboard-first workflow.

## Non-goals

- Mobile (Android/iOS), FastAPI/DB backend, galleries beyond the thumbnail strip, multi-user auth.

## Architecture

### Layers (kept / rewritten / new)

| Layer | Module | Status |
|---|---|---|
| Session model | `image_categorizer/model.py` | kept, unchanged |
| File ops | `image_categorizer/categorizer.py` | kept, unchanged |
| Storage | `image_categorizer/settings.py` | rewritten (new schema/format, same module name) |
| Metadata | `image_categorizer/metadata.py` | kept, unchanged (used by the Flet panel) |
| Old Tk UI | `image_categorizer/app.py`, `image_categorizer/viewer.py` | deleted |
| New Flet UI | `image_categorizer/ui/*.py` | new (controller + views) |
| Entry | `run.py`, `__main__`-safe console script | rewritten for Flet |

The pure-logic modules must not import `flet`; the UI layer must contain all framework code. Tests keep exercising the pure modules directly.

### UI structure (single page, state-rebuild)

- `ft.AppBar`: app title, theme light/dark toggle button, directory picker (desktop: native `FilePicker`; web: server-side path input, plus note that paths resolve on the serving machine), Filter/SearchBar over filenames, progress counter.
- Category chip-row (Material 3 filled Chips), numbered badges 1–9 mapped to keybinds; "+ Add category" opens the add dialog (folders created immediately on confirm; settings persisted).
- Main area: the current image scaled to fit available space via `ft.Image` + `ft.ScaleGestureDetector`/`ft.GestureDetector` (pinch zoom + wheel) and drag-to-pan; magnify/rotate only in view (display-only, parity with v2).
- Below image: metadata strip (File/Format/Dimensions/Size/EXIF lines from `describe`), toggle with `i`.
- Thumbnail strip (light extra): horizontal live strip of the next N remaining images, current one highlighted; click to jump.
- Actions bar: Mode toggle (Move/Copy), Subfolders toggle (On/Off), Skip, Undo; all also on keyboard.

### Keyboard parity (via `page.on_keyboard_event`)

- `1`–`9`: categorize into the n-th chip.
- `s`: skip; `u`: undo; `r`: rotate 90° CW; `i`: metadata toggle; `f`: focus filter.
- Category numbers are read from the current chip order, same "up to 9 accepted" rule as v2.

### Controller

`image_categorizer/ui/controller.py`: a plain-Python class owning `SessionModel` + `Categorizer` + a small state bag (filter text, theme, metadata-shown, viewer scale/offset) and methods `open_directory`, `categorize(idx)`, `skip`, `undo`, `rotate`, `toggle_*`, `current_image()` (fit-encoded for display), `refresh_strip()`. The view translates controller state into Flet controls; rebuilds are single-page diffs via `page.update()`. All file ops and state writes flow through the controller — views never touch the core directly.

### Persistence (new format)

- App settings: `~/.imagecategorizer/settings.json`, e.g. `{"categories": [...], "mode": "move"|"copy", "subfolders": bool, "theme": "system"|"dark"|"light", "last_dir": "", "rename_pattern": "{category}_{idx:04d}{ext}"}`. Unknown keys dropped on load; corrupt → defaults.
- Per-project resume state: `.imagecategorizer-state.json` in the open directory with `{"cursor": int, "processed": [str paths]}`; loaded bounds-guarded.
- `use_subfolders` in the old format is replaced by `subfolders`; old files are ignored (fresh defaults).

### Viewer behaviour

- Fit-to-container with max up to container width, wheel/pinch zoom (bounds 0.1–20 relative), drag pan, rotate resets zoom + re-fit; state resets per image. Zoom/pan are view-local (not persisted).
- Thumbnails: generated at a fixed max 120px height, `Image.open`-derived headers to keep memory small; cap strip to the next 12 under the current cursor.

### Deployment

- PyPI package `imagecategorizer` (dynamic version), console script `imagecategorizer` (desktop view by default; `imagecategorizer --web` serves web).
- Package deps: `flet>=1.0` (+ Pillow). Note: flet depends on its internal Flutter assets, installed through pip distribution only.
- Release pipeline on `v*` tags: PyPI (trusted publish), Windows exe (`flet pack` / `flet build windows` — plan researches and selects exact commands; both output a single executable), Linux AppImage (either from `flet pack` binary wrapped by appimagetool, or `flet build linux`). One file per target, same upload contract as v2 workflow otherwise.
- CI runs pytest + ruff on Python 3.10–3.14 matrix (floor moved to 3.10 per flet 1.0 constraints).

### Error handling

- No view-written file errors: `open_directory` (unreadable/empty dir) and failed file ops surface an inline `ft.SnackBar` marked as non-blocking; rename-pattern errors caught the same way (v2 fix parity: `OSError/KeyError/IndexError/ValueError`).
- Category names: same validation as v2's final fix (empty, duplicates — case-insensitive, characters in `<>:"/\|?*`, control chars, leading dot, trailing space/dot rejected; dirs created after validation; settings written only after a successful makedirs).

## Testing strategy

- Kept modules keep their 28-test suite, adapted to the new settings schema.
- Controller gets its own unit tests (pure Python, no flet launching): open/categorize/skip/undo round-trips, bounds, filter.
- UI files are minimal glue; no headless-flet UI test ladder in CI (flet headless testing is fragile) — controller tests + operator manual checks cover.

## Release verification (operator-triggered)

- Local rehearsal: `imagecategorizer` starts (headless probe) and `pytest`/`ruff` green. Real exe/AppImage builds happen via the release pipeline on the operator's tag; the plan prefers packaging commands verifiable in CI (operator's tag run shows real proof).
