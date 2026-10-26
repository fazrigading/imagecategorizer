import functools
import io

import flet as ft
from PIL import Image

from image_categorizer import settings as settings_mod
from image_categorizer.controller import Controller
from image_categorizer.ui import imagearea

# Control references shared between builders and _refresh(); single session only
# (desktop or one web client) — multi-client web sharing would need keying by page.id.
_state: dict = {}


def main_page(page: ft.Page):
    page.title = "Gading's Image Categorizer"
    cfg = settings_mod.load_settings()
    controller = Controller(cfg)
    page.theme_mode = _theme_mode(cfg.get("theme", "system"))
    _state.clear()
    _state["controller"] = controller
    _state["page"] = page

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
    # Limitation (flet 1.0.5): page-level keyboard events fire even while the
    # Filter TextField or a dialog input has focus, and neither Page nor
    # KeyboardEvent exposes which control is focused — so 1-9/s/u/r/i keys also
    # fire while typing in those fields. User must blur the field first;
    # revisit if a focused-control API lands in flet.
    c = controller
    k = e.key.lower()
    if k in "123456789":
        try:
            c.categorize(int(k) - 1)  # keys are 1-based chips, categorize is 0-based
        except Exception as exc:                      # noqa: BLE001 - surfaced by snack bar
            _snack(page, f"Error: {exc}")
    elif k == "s":
        c.skip()
    elif k == "u":
        try:
            c.undo()
        except Exception as exc:                      # noqa: BLE001 - surfaced by snack bar
            _snack(page, f"Error: {exc}")
    elif k == "r":
        imagearea.rotate_current()
    elif k == "i":
        c.meta_shown = not c.meta_shown
    elif k == "f":
        filter_field = _state.get("filter")
        if filter_field is not None:
            filter_field.focus()
    _refresh(page, controller)


def _snack(page, text):
    page.show_dialog(ft.SnackBar(ft.Text(text)))
    page.update()


def _refresh(page, controller):
    imagearea.refresh(controller)
    _state["counter"].value = (
        f"{controller.processed_count()}/{len(controller.model.images)}"
    )
    _state["undo"].disabled = not controller.can_undo()
    _state["dir_text"].value = _dir_label(controller, page)
    _state["meta_strip"].visible = controller.meta_shown
    _state["meta_text"].value = controller.describe_current() or ""
    _state["thumb_row"].controls = _thumb_controls(controller, page)
    page.update()


def _dir_label(controller, page):
    if page.web:
        return "Directory: not pickable in web mode (desktop only)"
    return f"Directory: {controller.source_dir or 'Pick a directory'}"


def _ensure_file_picker(page):
    picker = _state.get("file_picker")
    if picker is None:
        picker = ft.FilePicker()
        _state["file_picker"] = picker
        page.overlay.append(picker)
    return picker


def _handle_open_dir(controller, page, path):
    try:
        controller.open_directory(path)
    except (OSError, ValueError) as exc:
        _snack(page, f"Error: {exc}")
        return
    _rebuild_chips(controller, page)
    _refresh(page, controller)


def build_app_bar(controller, page):
    counter = ft.Text(f"{controller.processed_count()}/{len(controller.model.images)}")
    dir_text = ft.Text(_dir_label(controller, page))
    _state["counter"] = counter
    _state["dir_text"] = dir_text

    async def _pick_dir(_e):
        path = await _ensure_file_picker(page).get_directory_path(
            initial_directory=(
                controller.source_dir or controller.settings.get("last_dir") or None
            )
        )
        if path:
            _handle_open_dir(controller, page, path)

    def _toggle_theme(_e):
        controller.settings["theme"] = (
            "light" if controller.settings.get("theme") == "dark" else "dark"
        )
        settings_mod.save_settings(controller.settings)
        page.theme_mode = _theme_mode(controller.settings["theme"])
        page.update()

    actions = [counter, dir_text]
    if not page.web:
        actions.append(
            ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN,
                tooltip="Open directory",
                on_click=_pick_dir,
            )
        )
    actions.append(
        ft.IconButton(
            icon=ft.Icons.DARK_MODE,
            tooltip="Toggle dark/light theme",
            on_click=_toggle_theme,
        )
    )
    return ft.AppBar(title=ft.Text("Gading's Image Categorizer"), actions=actions)


def _chip_controls(controller, page):
    controls = []
    for i, name in enumerate(controller.categories()):

        def _cat(_e, idx=i):
            try:
                controller.categorize(idx)
            except Exception as exc:  # noqa: BLE001 - surfaced by snack bar
                _snack(page, f"Error: {exc}")
            _refresh(page, controller)

        controls.append(
            ft.FilledButton(
                f"{i + 1}. {name}",
                key=f"cat_{i}",
                on_click=_cat,
            )
        )
    return controls


def _rebuild_chips(controller, page):
    row = _state["chip_row"]
    row.controls = _chip_controls(controller, page)


def build_chip_bar(controller, page):
    row = ft.Row(spacing=8, wrap=True)
    row.controls = _chip_controls(controller, page)
    _state["chip_row"] = row

    def _add_cat(_e):
        field = ft.TextField(label="Category name", autofocus=True)

        def _confirm(_e):
            ok, msg = controller.add_category((field.value or "").strip())
            if not ok:
                _snack(page, f"Error: {msg}")
                return
            page.pop_dialog()
            _rebuild_chips(controller, page)
            _refresh(page, controller)

        dlg = ft.AlertDialog(
            title=ft.Text("Add category"),
            content=field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _e: page.pop_dialog()),
                ft.TextButton("Add", on_click=_confirm),
            ],
        )
        page.show_dialog(dlg)

    row.controls.append(ft.FilledButton("+ Add category", on_click=_add_cat))
    return row


def build_action_bar(controller, page):
    def _set_mode(_e):
        controller.settings["mode"] = "copy" if mode_switch.value else "move"
        mode_switch.label = f"mode: {controller.settings['mode']}"
        settings_mod.save_settings(controller.settings)
        page.update()

    def _set_subfolders(_e):
        controller.settings["subfolders"] = bool(sub_switch.value)
        settings_mod.save_settings(controller.settings)
        _snack(page, "Subfolders setting applies to the next directory open")

    def _skip(_e):
        controller.skip()
        _refresh(page, controller)

    def _do_undo(_e):
        try:
            controller.undo()
        except Exception as exc:  # noqa: BLE001 - surfaced by snack bar
            _snack(page, f"Error: {exc}")
        _refresh(page, controller)

    def _set_filter(e):
        controller.filter_text = e.data or ""
        _refresh(page, controller)

    mode_switch = ft.Switch(
        label=f"mode: {controller.settings.get('mode', 'move')}",
        value=controller.settings.get("mode") == "copy",
        on_change=_set_mode,
    )
    sub_switch = ft.Switch(
        label="subfolders",
        value=bool(controller.settings.get("subfolders")),
        on_change=_set_subfolders,
    )
    undo = ft.FilledButton(
        "Undo (u)",
        disabled=not controller.can_undo(),
        on_click=_do_undo,
    )
    filter_field = ft.TextField(
        label="Filter",
        value=controller.filter_text,
        on_change=_set_filter,
    )

    _state["undo"] = undo
    _state["filter"] = filter_field
    return ft.Row(
        [mode_switch, sub_switch, undo, ft.FilledButton("Skip (s)", on_click=_skip), filter_field],
        spacing=12,
    )


def build_thumb_strip(controller, page):
    row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8)
    row.controls = _thumb_controls(controller, page)
    _state["thumb_row"] = row
    return row


def _thumb_controls(controller, page):
    current = controller.current_image()
    controls = []
    for path in controller.thumbnails(12):
        selected = path == current
        controls.append(
            ft.Container(
                content=ft.Image(
                    src=_thumb_bytes(path),
                    fit=ft.BoxFit.SCALE_DOWN,
                    border_radius=6,
                ),
                width=90,
                height=90,
                border=ft.BorderSide(2, ft.Colors.PRIMARY) if selected else None,
                on_click=lambda e, p=path: _thumb_jump(controller, page, p),
            )
        )
    return controls


def _thumb_jump(controller, page, path):
    controller.jump_to(path)
    _refresh(page, controller)


@functools.lru_cache(maxsize=40)
def _thumb_bytes(path):
    try:
        with Image.open(path) as img:  # cached: full decode only once per path
            img.thumbnail((90, 90))
            img.save(buf := io.BytesIO(), format="PNG")
    except Exception:  # noqa: BLE001 — display-safe: drop thumbnail, keep app running
        return None
    return buf.getvalue()


def build_meta_strip(controller, page):
    text = ft.Text(
        controller.describe_current() or "",
        selectable=True,
    )
    strip = ft.Container(content=text, visible=controller.meta_shown)
    _state["meta_text"] = text
    _state["meta_strip"] = strip
    return strip
