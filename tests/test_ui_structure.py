def test_ui_imports():
    from image_categorizer.ui import app, imagearea
    for fn in (
        app.build_app_bar,
        app.build_chip_bar,
        app.build_action_bar,
        imagearea.build_image_area,
    ):
        assert callable(fn)


def test_controller_hot_path_ui_free():
    import ast  # noqa: F401 - kept per plan brief
    from pathlib import Path
    src = Path("image_categorizer/controller.py").read_text()
    assert "import flet" not in src, "controller must stay framework-free"
