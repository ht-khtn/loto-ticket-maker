"""Màn hình chính.

Mục tiêu:
- Bên trái: nhóm tuỳ chọn (template, grid, in ấn)
- Bên phải: preview vé (zoom/pan sau)

Hiện tại chỉ là khung để bắt đầu nhanh.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QFileDialog,
    QVBoxLayout,
    QWidget,
)

from ..config.defaults import DEFAULT_GRID, DEFAULT_PRINT, DEFAULT_TEMPLATE
from ..core.loto_3x9 import generate_loto_3x9
from ..export.pdf_exporter import export_tickets_a4_pdf
from ..render.ticket_renderer import render_ticket_preview
from .image_utils import pil_to_qpixmap


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Loto Ticket Maker")
        self.resize(1200, 720)

        root = QWidget(self)
        self.setCentralWidget(root)

        # Apply simple styling
        try:
            from importlib.resources import files

            qss_path = files(__package__).joinpath("style.qss")
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        except Exception:
            pass

        layout = QHBoxLayout(root)

        # Sidebar
        sidebar = QFrame(root)
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar.setProperty("panel", True)
        sidebar.setFixedWidth(360)
        sidebar_layout = QVBoxLayout(sidebar)

        sidebar_layout.addWidget(self._build_template_group(sidebar))
        sidebar_layout.addWidget(self._build_grid_group(sidebar))
        sidebar_layout.addWidget(self._build_print_group(sidebar))

        btn_generate = QPushButton("Tạo vé (preview)")
        btn_export = QPushButton("Xuất PDF (A4)")
        sidebar_layout.addWidget(btn_generate)
        sidebar_layout.addWidget(btn_export)
        sidebar_layout.addStretch(1)

        btn_generate.clicked.connect(self._on_generate_preview)
        btn_export.clicked.connect(self._on_export_pdf)

        # Preview area
        preview_container = QFrame(root)
        preview_container.setFrameShape(QFrame.StyledPanel)
        preview_container.setProperty("panel", True)
        preview_layout = QVBoxLayout(preview_container)

        title = QLabel("Preview")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.preview_label = QLabel("Bấm 'Tạo vé (preview)' để xem vé 3x9")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(500)
        self.preview_label.setStyleSheet("background: #111827; border-radius: 10px;")

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

        self._last_preview: QPixmap | None = None
        self._last_seed: int | None = None

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
        self.rows = QSpinBox()
        self.rows.setRange(3, 3)
        self.rows.setValue(DEFAULT_GRID.rows)
        lay.addWidget(self.rows, 0, 1)

        lay.addWidget(QLabel("Cột"), 1, 0)
        self.cols = QSpinBox()
        self.cols.setRange(9, 9)
        self.cols.setValue(DEFAULT_GRID.cols)
        lay.addWidget(self.cols, 1, 1)

        lay.addWidget(QLabel("Seed"), 2, 0)
        self.seed = QSpinBox()
        self.seed.setRange(0, 2_000_000_000)
        self.seed.setValue(0)
        self.seed.setToolTip("0 = random; số khác 0 để tái tạo vé")
        lay.addWidget(self.seed, 2, 1)

        lay.addWidget(QLabel("Số vé xuất"), 3, 0)
        self.ticket_count = QSpinBox()
        self.ticket_count.setRange(1, 200)
        self.ticket_count.setValue(6)
        lay.addWidget(self.ticket_count, 3, 1)

        hint = QLabel("Luật đang dùng: Loto VN 3x9 (15 số/vé, mỗi hàng 5 số)")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6B7280;")
        lay.addWidget(hint, 4, 0, 1, 2)
        return box

    def _build_print_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("In ấn (PDF)", parent)
        lay = QGridLayout(box)

        lay.addWidget(QLabel("Khổ giấy"), 0, 0)
        lay.addWidget(QLabel("A4"), 0, 1)

        lay.addWidget(QLabel("Vé / hàng"), 1, 0)
        self.per_row = QSpinBox()
        self.per_row.setRange(1, 6)
        self.per_row.setValue(2)
        lay.addWidget(self.per_row, 1, 1)

        lay.addWidget(QLabel("Vé / cột"), 2, 0)
        self.per_col = QSpinBox()
        self.per_col.setRange(1, 8)
        self.per_col.setValue(3)
        lay.addWidget(self.per_col, 2, 1)

        note = QLabel("Gợi ý: 2x3 = 6 vé/trang (tuỳ kích thước vé & lề).")
        note.setWordWrap(True)
        note.setStyleSheet("color: #6B7280;")
        lay.addWidget(note, 3, 0, 1, 2)
        return box

    def _on_generate_preview(self) -> None:
        seed_value = self.seed.value()
        seed = None if seed_value == 0 else seed_value
        numbers = generate_loto_3x9(seed=seed)

        img = render_ticket_preview(DEFAULT_TEMPLATE, DEFAULT_GRID, numbers=numbers, scale=5.0)
        pix = pil_to_qpixmap(img)

        self._last_preview = pix
        self._last_seed = seed
        self.preview_label.setPixmap(pix)

    def _on_export_pdf(self) -> None:
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Xuất PDF",
            "loto_tickets_a4.pdf",
            "PDF Files (*.pdf)",
        )
        if not out_path:
            return

        seed_value = self.seed.value()
        base_seed = None if seed_value == 0 else seed_value
        count = self.ticket_count.value()

        tickets: list[list[list[int | None]]] = []
        for i in range(count):
            seed = None if base_seed is None else base_seed + i
            tickets.append(generate_loto_3x9(seed=seed))

        try:
            export_tickets_a4_pdf(
                out_path=out_path,
                template=DEFAULT_TEMPLATE,
                grid=DEFAULT_GRID,
                print_spec=DEFAULT_PRINT,
                tickets=tickets,
                per_row=self.per_row.value(),
                per_col=self.per_col.value(),
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất PDF", str(e))
            return

        QMessageBox.information(self, "OK", f"Đã xuất PDF: {out_path}")
