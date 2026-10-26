import math

import flet as ft

# Single session only (desktop / one web client)
_state = {
    "image": None,      # ft.Image | None
    "container": None,  # ft.Container | None
    "scale": 1.0,
    "off": (0.0, 0.0),
    "path": None,
    "rot": 0,  # degrees, clockwise
}
MIN_SCALE, MAX_SCALE = 0.1, 20.0


def build_image_area(controller):
    image = ft.Image(
        src=None,
        expand=True,
        fit=ft.BoxFit.CONTAIN,
        border_radius=10,
    )
    detector = ft.GestureDetector(
        content=image,
        drag_interval=10,
        on_scroll=_on_scroll,
        on_scale_update=_on_scale_update,
        on_pan_update=_on_pan_update,
    )
    container = ft.Container(
        content=detector, expand=True, alignment=ft.Alignment.CENTER
    )
    _state["image"] = image
    _state["container"] = container
    return container


def refresh(controller):
    img = controller.current_image()
    if _state["image"] is None:
        return
    if img != _state["path"]:
        _state["path"] = img
        _state["scale"] = 1.0
        _state["off"] = (0.0, 0.0)
        _state["rot"] = 0
        image = _state["image"]
        if img is None:
            image.src = None
        else:
            image.src = _to_src(img)
    _apply()


def rotate_current():
    # Spec: rotate resets zoom and re-fits
    _state["scale"] = 1.0
    _state["off"] = (0.0, 0.0)
    _state["rot"] = (_state["rot"] + 90) % 360
    _apply()


def _to_src(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None  # silent-safe: show empty frame rather than crash


def _apply():
    image, container = _state["image"], _state["container"]
    if image is None:
        return
    image.scale = _state["scale"]
    image.rotate = ft.Rotate(
        round(math.radians(_state["rot"]), 4), alignment=ft.Alignment.CENTER
    )
    if container is not None:
        container.offset = ft.Offset(*_state["off"])
    _sync(image)
    _sync(container)


def _sync(ctrl):
    try:
        ctrl.update()
    except RuntimeError:
        pass  # Control must be added to the page first — not attached yet


def _on_scroll(e):
    # Flutter semantics: scroll_delta.y > 0 is a wheel-down tick, y < 0 is
    # wheel-up. Wheel-up zooms in (standard viewer convention).
    zoom_in = e.scroll_delta.y < 0
    factor = 1.25 if zoom_in else 0.8
    old = _state["scale"]
    _state["scale"] = min(max(old * factor, MIN_SCALE), MAX_SCALE)
    if _state["image"]:
        _state["image"].scale = _state["scale"]
    _sync(_state["image"])


def _on_scale_update(e):
    old = _state["scale"]
    _state["scale"] = min(max(old * e.scale, MIN_SCALE), MAX_SCALE)
    if _state["image"]:
        _state["image"].scale = _state["scale"]
    _sync(_state["image"])


def _on_pan_update(e):
    d = e.local_delta
    if d is None:
        return
    off = _state["off"]
    # No clamping: position resets on next image, so pan can't lose the image.
    _state["off"] = (off[0] + d.x, off[1] + d.y)
    if _state["container"]:
        _state["container"].offset = ft.Offset(*_state["off"])
        _sync(_state["container"])
