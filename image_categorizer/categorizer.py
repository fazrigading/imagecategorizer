from __future__ import annotations

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
