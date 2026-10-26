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
        if self.categorizer is None or self.model.finished():
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

    def skip(self, *_args):
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
    ImageCategorizerApp(root)
    root.configure(background="black")
    root.mainloop()


if __name__ == "__main__":
    main()
