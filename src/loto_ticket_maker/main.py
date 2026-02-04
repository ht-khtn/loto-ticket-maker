"""Entrypoint của ứng dụng.

Chạy:
    python -m loto_ticket_maker
"""

from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from .ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Loto Ticket Maker")

    window = MainWindow()
    window.show()

    return app.exec()
