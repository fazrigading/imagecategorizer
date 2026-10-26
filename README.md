# imagecategorizer

Fast single-image triage for classification datasets: open a folder,
categorize one photo at a time with the keyboard, files land in
per-category subfolders. Built on [Flet](https://flet.dev) — the same app
runs as a desktop window or in a web browser.

## Install

```bash
pip install imagecategorizer
```

No Python needed? Grab the Windows `.exe` or Linux `.AppImage` from the
[Releases](https://github.com/fazrigading/imagecategorizer/releases) page.

## Run

Desktop:

```bash
imagecategorizer
```

Web:

```bash
imagecategorizer --web
```

(From a source checkout, `main.py` works the same way, as does `flet run`
/ `flet run --web`.)

Then pick a directory with the folder button and work the keyboard.

## Keyboard

| Key | Action |
|-----|--------|
| **1–9** | Assign the current image to category N |
| **s** | Skip (leave in place, move on) |
| **u** | Undo the last action (a move reverts; a copied copy is deleted) |
| **r** | Rotate the display 90° clockwise (display only) |
| **i** | Toggle the metadata strip (name, format, dimensions, size, EXIF) |
| **f** | Focus the filter field (type to narrow the thumbnail strip by filename) |

On-screen equivalents exist for everything: category buttons (1–9), Skip
and Undo buttons, the filter field, the metadata strip toggle is implicit
in the strip, and clicking a thumbnail in the strip jumps to that image.

The **mode** switch toggles copy vs move and **subfolders** switch
includes subdirectories on the next directory open; both persist.
"+ Add category" creates the destination folder on disk and its button
instantly.

## Storage

- App-wide preferences: `~/.imagecategorizer/settings.json`
  - Keys: `categories`, `mode`, `subfolders`, `theme`, `last_dir`,
    `rename_pattern`
- Per-directory session progress: `.imagecategorizer-state.json` inside
  the source folder (cursor position + processed list), so closing and
  reopening — even on another machine via sync — resumes where you
  stopped.

`rename_pattern` is power-user only (no UI): a Python format string
applied when organizing files into categories, e.g.
`"{category}_{idx:04d}{ext}"` turns `photo.jpg` into `infected_0001.jpg`.
Valid fields: `category`, `idx`, `ext`.

## Web mode caveat

In web mode, file and directory access resolve on the machine serving
the app, not the browser's machine — and the directory picker is
disabled (open the app with a directory already in play on that server,
or run desktop mode to pick one). Also note one-client-at-a-time: the
current build is not safe to share across concurrent browser clients.

## Packaging

Builds ship as portable binaries (`.exe` for Windows, `.AppImage` for
Linux) plus the standard PyPI installation; CI produces these on tagged
releases.

## Development

```bash
pip install -e .
pytest
```
