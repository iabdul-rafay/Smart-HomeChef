import sys

from PyQt6.QtWidgets import QApplication

try:
    from homechef.ui_pyqt6 import HomeChefWindow
except Exception:  # fallback if PyQt6 window not available
    HomeChefWindow = None  # type: ignore
    from homechef.ui import HomeChefWidget


def main() -> int:
    app = QApplication(sys.argv)
    if HomeChefWindow is not None:
        w = HomeChefWindow()
    else:
        w = HomeChefWidget()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


