import sys


def main():
    from image_categorizer.ui.app import main_page

    web = "--web" in sys.argv[1:]
    import flet as ft

    ft.run(
        main_page,
        view=ft.AppView.WEB_BROWSER if web else ft.AppView.FLET_APP,
    )


if __name__ == "__main__":
    main()
