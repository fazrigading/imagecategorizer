# imagecategorizer

Fast single-image triage for classification datasets: open a folder,
categorize one photo at a time with the keyboard, files land in
per-category subfolders.

## Install

```bash
pip install imagecategorizer
```

No Python needed? Download the Windows `.exe` or Linux `.AppImage` from the
[Releases](https://github.com/fazrigading/imagecategorizer/releases) page.

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
