import functools
import io
import os

import flet as ft
from PIL import Image

from image_categorizer import __version__
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
    controller.counter_mode = "simple"
    page.theme_mode = _theme_mode(cfg.get("theme", "system"))
    _state.clear()
    _state["controller"] = controller
    _state["page"] = page

    page.on_keyboard_event = lambda e: _on_key(controller, page, e)

    # -- app bar: menu (left), counter (center), directory + theme (right)
    page.appbar = build_app_bar(controller, page)

    page.add(
        build_top_bar(controller, page),
        imagearea.build_image_area(controller),
        build_thumb_strip(controller, page),
        build_meta_strip(controller, page),
    )

    # Auto-resume: re-open last directory if it still exists
    last = cfg.get("last_dir") or ""
    if last and os.path.isdir(last):
        _handle_open_dir(controller, page, last)

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


def _counter_text(controller):
    """Middle-top counter; View menu selects simple / per-category / both."""
    processed = controller.processed_count()
    total = len(controller.model.images)
    if not controller.source_dir:
        return "0/0"
    mode = getattr(controller, "counter_mode", "simple")
    if mode == "simple":
        return f"{processed}/{total}"
    counts, skipped = controller.count_categories()
    cats = " · ".join(f"{n}: {counts.get(n, 0)}" for n in controller.categories())
    line = f"{cats} · skip: {skipped}"
    if mode == "both":
        return f"{processed}/{total} — {line}"
    return line


def _refresh(page, controller):
    imagearea.refresh(controller)
    counter = _state.get("counter")
    if counter is not None:
        counter.value = _counter_text(controller)
    _state["undo"].disabled = not controller.can_undo()
    _state["dir_text"].value = _dir_label(controller, page)
    web_field = _state.get("web_dir_field")
    if web_field is not None:
        web_field.value = controller.source_dir or web_field.value
    _state["meta_strip"].visible = controller.meta_shown
    _state["meta_text"].value = controller.describe_current() or ""
    _state["thumb_row"].controls = _thumb_controls(controller, page)
    page.update()


def _dir_label(controller, page):
    if page.web:
        return "Directory: type a path on the server to open"
    return f"Directory: {controller.source_dir or 'Pick a directory'}"


def _ensure_file_picker(page):
    # FilePicker is a Service in flet 1.x — it attaches to page.services,
    # NOT page.overlay (overlay would raise "Unknown control" at raise time).
    picker = _state.get("file_picker")
    if picker is None:
        picker = ft.FilePicker()
        _state["file_picker"] = picker
        page.services.append(picker)
        page.update()
    return picker


def _handle_open_dir(controller, page, path):
    try:
        controller.open_directory(path)
    except (OSError, ValueError) as exc:
        _snack(page, f"Error: {exc}")
        return
    _rebuild_chips(controller, page)
    _refresh(page, controller)


def _pick_dir_and_refresh(controller, page):
    async def _handler(_e):
        path = await _ensure_file_picker(page).get_directory_path(
            initial_directory=(
                controller.source_dir or controller.settings.get("last_dir") or None
            )
        )
        if path:
            _handle_open_dir(controller, page, path)

    return _handler


# -- top area: menu bar in the app bar; chips + actions below it ------------


def build_app_bar(controller, page):
    counter = ft.Text(_counter_text(controller), size=16, weight=ft.FontWeight.BOLD)
    dir_text = ft.Text(_dir_label(controller, page))
    _state["counter"] = counter
    _state["dir_text"] = dir_text

    actions = [dir_text]
    if page.web:
        # Web: paths resolve on the serving machine, so offer a text input
        field = ft.TextField(
            value=controller.source_dir or controller.settings.get("last_dir", ""),
            width=320, dense=True,
            tooltip="Directory path on the server machine",
        )

        def _open_web_dir(_e):
            _handle_open_dir(controller, page, field.value or "")

        _state["web_dir_field"] = field
        actions += [field, ft.TextButton("Open", on_click=_open_web_dir)]
    else:
        actions.append(
            ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN,
                tooltip="Open directory",
                on_click=_pick_dir_and_refresh(controller, page),
            )
        )
    actions.append(_theme_button(controller, page))
    return ft.AppBar(leading=build_menu_buttons(controller, page), title=counter,
                     center_title=True, actions=actions)


def _theme_button(controller, page):
    async def _toggle_theme(_e):
        controller.settings["theme"] = (
            "light" if controller.settings.get("theme") == "dark" else "dark"
        )
        settings_mod.save_settings(controller.settings)
        page.theme_mode = _theme_mode(controller.settings["theme"])
        page.update()

    return ft.IconButton(
        icon=ft.Icons.DARK_MODE,
        tooltip="Toggle dark/light theme",
        on_click=_toggle_theme,
    )


def _counter_mode_items(controller, page):
    items = []
    for mode, label in (
        ("simple", "Counter: simple (x/y)"),
        ("extended", "Counter: per-category"),
        ("both", "Counter: both"),
    ):
        active = getattr(controller, "counter_mode", "simple") == mode

        def _set(_e, m=mode):
            controller.counter_mode = m
            counter = _state.get("counter")
            if counter is not None:
                counter.value = _counter_text(controller)
            page.appbar = build_app_bar(controller, page)  # re-check the menu tick
            page.update()

        items.append(
            ft.PopupMenuItem(content=ft.Text(label), checked=active, on_click=_set)
        )
    return items


def _about_dialog():
    def _open(_e):
        _state["page"].show_dialog(
            ft.AlertDialog(
                title=ft.Text("Image Categorizer"),
                content=ft.Text(
                    f"Gading's Image Categorizer v{__version__}\n\n"
                    "Keyboard triage for image datasets, built with Flet.\n"
                    "Help: see the keybinds listed in the project README."
                ),
                actions=[ft.TextButton("Close", on_click=lambda _e: _state["page"].pop_dialog())],
            )
        )

    return _open


def build_menu_buttons(controller, page):
    """App bar buttons replacing the old MenuBar: File / Edit / View / Help."""
    def _edit_categories(_e):
        page.show_dialog(_edit_categories_dialog(controller, page))

    def _meta_toggle(_e):
        controller.meta_shown = not controller.meta_shown
        _refresh(page, controller)

    def _popup(text, items, tooltip):
        return ft.PopupMenuButton(
            content=ft.Text(text),
            items=items,
            tooltip=tooltip,
        )

    return ft.Row(
        [
            _popup("File", [
            (
                ft.PopupMenuItem(
                    content=ft.Text("Open Directory..."),
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=_pick_dir_and_refresh(controller, page)
                    if not page.web
                    else (lambda _e: None),  # web: native picker unsupported
                )
            ),
            _exit_menu_item(page),
        ], "File"),
        _popup("Edit", [
            ft.PopupMenuItem(
                content=ft.Text("Edit categories..."),
                icon=ft.Icons.EDIT,
                on_click=_edit_categories,
            ),
        ], "Edit"),
        _popup("View", [
            *_counter_mode_items(controller, page),
            ft.PopupMenuItem(
                content=ft.Text("Show metadata"),
                icon=ft.Icons.INFO,
                on_click=_meta_toggle,
            ),
            _theme_menu_item(controller, page),
        ], "View"),
        _popup("Help", [
            ft.PopupMenuItem(
                content=ft.Text("About..."),
                icon=ft.Icons.HELP,
                on_click=_about_dialog(),
            ),
        ], "Help"),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _exit_menu_item(page):
    async def _exit(_e):
        if not page.web and getattr(page, "window", None) is not None:
            try:
                await page.window.close()
            except RuntimeError:
                pass  # window may be unavailable in embedded/themeless runs

    return ft.PopupMenuItem(content=ft.Text("Exit"), on_click=_exit)


def _theme_menu_item(controller, page):
    async def _toggle(_e):
        controller.settings["theme"] = (
            "light" if controller.settings.get("theme") == "dark" else "dark"
        )
        settings_mod.save_settings(controller.settings)
        page.theme_mode = _theme_mode(controller.settings["theme"])
        page.update()

    return ft.PopupMenuItem(
        content=ft.Text("Toggle dark/light theme"),
        icon=ft.Icons.DARK_MODE,
        on_click=_toggle,
    )


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
    if controller.source_dir:  # counts may have shifted on an edit
        _refresh(page, controller)


def build_chip_bar(controller, page):
    row = ft.Row(spacing=8, wrap=True, run_spacing=8, scroll=ft.ScrollMode.AUTO)
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


def _edit_categories_dialog(controller, page):
    rows = []

    def _apply(_e):
        original = list(controller.categories())
        used = set()
        for entry, orig in rows:
            new = (entry.value or "").strip()
            if new == orig:
                used.add(orig)
                continue
            if new:
                ok, msg = controller.rename_category(orig, new)
                if not ok:
                    _snack(page, f"Error: {msg}")
                    return
                used.add(new)
        # entries blanked by the user are deletions
        for orig in original:
            if orig not in used:
                ok, msg = controller.remove_category(orig)
                if not ok:
                    _snack(page, f"Error: {msg}")
                    return
        page.pop_dialog()
        _rebuild_chips(controller, page)
        _refresh(page, controller)

    for name in controller.categories():
        entry = ft.TextField(value=name, expand=True)
        rows.append((entry, name))

    def _remove(entry, orig):
        async def _del(_e):
            entry.value = ""
            entry.update()
        return _del

    content = ft.Column(
        [
            ft.Row([entry, ft.IconButton(ft.Icons.DELETE, on_click=_remove(entry, orig))])
            for entry, orig in rows
        ],
        tight=True, scroll=ft.ScrollMode.AUTO,
    )

    return ft.AlertDialog(
        title=ft.Text("Edit categories"),
        content=content,
        actions=[
            ft.TextButton("Cancel", on_click=lambda _e: page.pop_dialog()),
            ft.TextButton("Save", on_click=_apply),
        ],
    )


# -- action controls live top-right, under the directory, next to chips ----


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
        width=160,
    )
    _state["undo"] = undo
    _state["filter"] = filter_field
    return [
        mode_switch,
        sub_switch,
        undo,
        ft.FilledButton("Skip (s)", on_click=_skip),
        filter_field,
    ]


def build_top_bar(controller, page):
    """Chips (left) + mode/subfolders/undo/skip/filter (right), in one top row."""
    return ft.Row(
        [
            build_chip_bar(controller, page),
            ft.Row(build_action_bar(controller, page), spacing=12, wrap=True),
        ],
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# -- thumbnail strip: prev / next buttons scroll the row --------------------


def build_thumb_strip(controller, page):
    row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8, expand=True)
    row.controls = _thumb_controls(controller, page)
    _state["thumb_row"] = row
    # flet awaits only handlers that are themselves coroutine functions
    # (base_control.py:516) — lambdas returning a coroutine never get awaited.
    return ft.Row(
        [
            ft.IconButton(
                ft.Icons.CHEVRON_LEFT,
                on_click=_thumb_scroll_back,
                tooltip="Scroll strip back",
            ),
            row,
            ft.IconButton(
                ft.Icons.CHEVRON_RIGHT,
                on_click=_thumb_scroll_forward,
                tooltip="Scroll strip forward",
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _thumb_row():
    row = _state.get("thumb_row")
    if row is not None and row.controls:
        return row
    return None


async def _thumb_scroll_back(_e):
    row = _thumb_row()
    if row is not None:
        await row.scroll_to(delta=-360, duration=200)


async def _thumb_scroll_forward(_e):
    row = _thumb_row()
    if row is not None:
        await row.scroll_to(delta=360, duration=200)


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
