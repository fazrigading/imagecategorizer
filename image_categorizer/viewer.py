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
        self._rotate_deg = 0
        self._scale = 1.0
        self._x = self._y = 0  # top-left draw position
        self._photo = None
        self._path = None
        self.bind("<Configure>", lambda e: self.show(self._path) if self._path else None)
        self.bind("<MouseWheel>", self._zoom)        # Windows/macOS
        self.bind("<Button-4>", self._zoom)          # X11 wheel up
        self.bind("<Button-5>", self._zoom)          # X11 wheel down
        self.bind("<ButtonPress-2>", self._pan_start)
        self.bind("<B2-Motion>", self._pan_move)

    # -- load ------------------------------------------------------------------
    def show(self, path):
        self._path = path
        self.delete("all")
        self._photo = None
        self._rotate_deg = 0
        self._rotated = None
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
        self._rotated = self._pil.rotate(self._rotate_deg, expand=True) if self._rotate_deg else self._pil
        can_w = max(self.winfo_width(), 1)
        can_h = max(self.winfo_height(), 1)
        w, h = fit_size(self._rotated.width, self._rotated.height, can_w, can_h)
        self._scale = w / self._rotated.width
        self._x, self._y = (can_w - w) // 2, (can_h - h) // 2
        self._render(w, h)

    def _render(self, w: int, h: int):
        self.delete("all")
        resized = self._rotated.resize((max(w, 1), max(h, 1)), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(resized, master=self)
        self.create_image(self._x, self._y, image=self._photo, anchor="nw")

    # shortcut: full re-render per zoom step, fine to ~20MP; switch to crop-based zoom only if real sessions hit it.
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
