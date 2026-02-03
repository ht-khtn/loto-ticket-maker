"""Màn hình chính.

Mục tiêu:
- Bên trái: nhóm tuỳ chọn (template, grid, in ấn)
- Bên phải: preview vé (zoom/pan sau)

Hiện tại chỉ là khung để bắt đầu nhanh.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Loto Ticket Maker")
        self.resize(1200, 720)

        root = QWidget(self)
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)

        # Sidebar
        sidebar = QFrame(root)
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar.setFixedWidth(360)
        sidebar_layout = QVBoxLayout(sidebar)

        sidebar_layout.addWidget(self._build_template_group(sidebar))
        sidebar_layout.addWidget(self._build_grid_group(sidebar))
        sidebar_layout.addWidget(self._build_print_group(sidebar))

        btn_generate = QPushButton("Tạo vé (preview)")
        btn_export = QPushButton("Xuất PDF")
        sidebar_layout.addWidget(btn_generate)
        sidebar_layout.addWidget(btn_export)
        sidebar_layout.addStretch(1)

        # Preview area
        preview_container = QFrame(root)
        preview_container.setFrameShape(QFrame.StyledPanel)
        preview_layout = QVBoxLayout(preview_container)

        title = QLabel("Preview")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.preview_label = QLabel("(Sắp có render vé ở đây)")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(500)
        self.preview_label.setStyleSheet(
            "background: #111827; color: #E5E7EB; border-radius: 8px;"
        )

        scroll = QScrollArea(preview_container)
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.addWidget(self.preview_label)
        inner_layout.addStretch(1)
        scroll.setWidget(inner)

        preview_layout.addWidget(title)
        preview_layout.addWidget(scroll)

        layout.addWidget(sidebar)
        layout.addWidget(preview_container, 1)

    def _build_template_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Nền vé (template)", parent)
        lay = QVBoxLayout(box)
        lay.addWidget(QLabel("- Bước sau: chọn ảnh nền / tạo nền trắng"))
        lay.addWidget(QLabel("- Chọn kích thước vé theo mm"))
        return box

    def _build_grid_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Ô số (grid)", parent)
        lay = QGridLayout(box)

        lay.addWidget(QLabel("Hàng"), 0, 0)
        rows = QSpinBox()
        rows.setRange(1, 20)
        rows.setValue(3)
        lay.addWidget(rows, 0, 1)

        lay.addWidget(QLabel("Cột"), 1, 0)
        cols = QSpinBox()
        cols.setRange(1, 20)
        cols.setValue(9)
        lay.addWidget(cols, 1, 1)

        hint = QLabel("Gợi ý: 3x9 là kiểu loto VN; 5x5 là kiểu bingo")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6B7280;")
        lay.addWidget(hint, 2, 0, 1, 2)
        return box

    def _build_print_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("In ấn (PDF)", parent)
        lay = QVBoxLayout(box)
        lay.addWidget(QLabel("- Bước sau: chọn khổ giấy (A4/A5/custom)"))
        lay.addWidget(QLabel("- In nhiều vé/trang, chỉnh lề, khoảng cách"))
        return box
