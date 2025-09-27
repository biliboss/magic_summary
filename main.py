from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.controller import ProcessingController


def main() -> int:
    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)
    window = MainWindow()
    ProcessingController(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
