import image_categorizer


def test_package_exports_version():
    assert image_categorizer.__version__ == "0.2.0"


def test_app_module_exposes_main():
    from image_categorizer.app import main

    assert callable(main)
