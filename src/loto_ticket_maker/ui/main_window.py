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
    QComboBox,
    QDoubleSpinBox,
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
from ..config.presets import load_preset, save_preset
from ..core.loto_15x6 import generate_loto_15x6
from ..core.models import GridSpec, PrintSpec, TicketTemplateSpec
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

            package_name = __package__ or "loto_ticket_maker.ui"
            qss_path = files(package_name).joinpath("style.qss")
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        except Exception:
            pass

        layout = QHBoxLayout(root)

        # Sidebar
        sidebar = QFrame(root)
        sidebar.setFrameShape(QFrame.Shape.StyledPanel)
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
        preview_container.setFrameShape(QFrame.Shape.StyledPanel)
        preview_container.setProperty("panel", True)
        preview_layout = QVBoxLayout(preview_container)

        title = QLabel("Preview")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.preview_label = QLabel("Bấm 'Tạo vé (preview)' để xem vé 15x6")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

        self._background_path: str | None = DEFAULT_TEMPLATE.background_path

    def _build_template_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Nền vé (template)", parent)
        lay = QGridLayout(box)

        lay.addWidget(QLabel("Rộng (mm)"), 0, 0)
        self.template_w = QDoubleSpinBox()
        self.template_w.setRange(40.0, 600.0)
        self.template_w.setDecimals(1)
        self.template_w.setSingleStep(1.0)
        self.template_w.setValue(DEFAULT_TEMPLATE.width_mm)
        lay.addWidget(self.template_w, 0, 1)

        lay.addWidget(QLabel("Cao (mm)"), 1, 0)
        self.template_h = QDoubleSpinBox()
        self.template_h.setRange(40.0, 600.0)
        self.template_h.setDecimals(1)
        self.template_h.setSingleStep(1.0)
        self.template_h.setValue(DEFAULT_TEMPLATE.height_mm)
        lay.addWidget(self.template_h, 1, 1)

        self.bg_label = QLabel("(không có ảnh nền)")
        self.bg_label.setWordWrap(True)
        self.bg_label.setStyleSheet("color: #93C5FD;")
        lay.addWidget(QLabel("Ảnh nền"), 2, 0)
        lay.addWidget(self.bg_label, 2, 1)

        btn_bg = QPushButton("Chọn ảnh nền…")
        btn_bg_clear = QPushButton("Xoá")
        btn_bg.clicked.connect(self._on_choose_background)
        btn_bg_clear.clicked.connect(self._on_clear_background)
        lay.addWidget(btn_bg, 3, 0)
        lay.addWidget(btn_bg_clear, 3, 1)

        btn_load = QPushButton("Mở preset…")
        btn_save = QPushButton("Lưu preset…")
        btn_load.clicked.connect(self._on_load_preset)
        btn_save.clicked.connect(self._on_save_preset)
        lay.addWidget(btn_load, 4, 0)
        lay.addWidget(btn_save, 4, 1)

        self._refresh_template_ui()
        return box

    def _build_grid_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Ô số (grid)", parent)
        lay = QGridLayout(box)

        lay.addWidget(QLabel("Hàng"), 0, 0)
        self.rows = QSpinBox()
        self.rows.setRange(15, 15)
        self.rows.setValue(15)
        lay.addWidget(self.rows, 0, 1)

        lay.addWidget(QLabel("Cột"), 1, 0)
        self.cols = QSpinBox()
        self.cols.setRange(6, 6)
        self.cols.setValue(6)
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

        hint = QLabel(
            "Luật đang dùng: 15x6 (đủ 1..60, mỗi hàng 2 ô trống, trống theo cột 6-5-5-5-5-4)"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6B7280;")
        lay.addWidget(hint, 4, 0, 1, 2)
        return box

    def _build_print_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("In ấn (PDF)", parent)
        lay = QGridLayout(box)

        lay.addWidget(QLabel("Khổ giấy"), 0, 0)
        self.page_size = QComboBox()
        self.page_size.addItems(["A4", "A5"])
        self.page_size.setCurrentText(DEFAULT_PRINT.page_size.upper())
        lay.addWidget(self.page_size, 0, 1)

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

        lay.addWidget(QLabel("Lề (mm)"), 3, 0)
        self.margin_mm = QDoubleSpinBox()
        self.margin_mm.setRange(0.0, 50.0)
        self.margin_mm.setDecimals(1)
        self.margin_mm.setSingleStep(1.0)
        self.margin_mm.setValue(DEFAULT_PRINT.margin_mm)
        lay.addWidget(self.margin_mm, 3, 1)

        lay.addWidget(QLabel("Khoảng cách (mm)"), 4, 0)
        self.spacing_mm = QDoubleSpinBox()
        self.spacing_mm.setRange(0.0, 50.0)
        self.spacing_mm.setDecimals(1)
        self.spacing_mm.setSingleStep(1.0)
        self.spacing_mm.setValue(DEFAULT_PRINT.spacing_mm)
        lay.addWidget(self.spacing_mm, 4, 1)

        note = QLabel("Gợi ý: 2x3 = 6 vé/trang (tuỳ kích thước vé & lề).")
        note.setWordWrap(True)
        note.setStyleSheet("color: #6B7280;")
        lay.addWidget(note, 5, 0, 1, 2)
        return box

    def _refresh_template_ui(self) -> None:
        if self._background_path:
            self.bg_label.setText(self._background_path)
        else:
            self.bg_label.setText("(không có ảnh nền)")

    def _current_template(self) -> TicketTemplateSpec:
        return TicketTemplateSpec(
            width_mm=float(self.template_w.value()),
            height_mm=float(self.template_h.value()),
            background_path=self._background_path,
        )

    def _current_grid(self) -> GridSpec:
        return GridSpec(
            rows=int(self.rows.value()),
            cols=int(self.cols.value()),
            padding_mm=DEFAULT_GRID.padding_mm,
            line_width_mm=DEFAULT_GRID.line_width_mm,
        )

    def _current_print(self) -> PrintSpec:
        return PrintSpec(
            page_size=str(self.page_size.currentText()),
            margin_mm=float(self.margin_mm.value()),
            spacing_mm=float(self.spacing_mm.value()),
        )

    def _on_choose_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh nền",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        self._background_path = path
        self._refresh_template_ui()

    def _on_clear_background(self) -> None:
        self._background_path = None
        self._refresh_template_ui()

    def _on_load_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Mở preset",
            "",
            "JSON Files (*.json)",
        )
        if not path:
            return

        try:
            template, grid, print_spec = load_preset(path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi preset", str(e))
            return

        self.template_w.setValue(template.width_mm)
        self.template_h.setValue(template.height_mm)
        self._background_path = template.background_path
        self._refresh_template_ui()

        # Grid hiện đang cố định 15x6 theo RULE.md
        self.rows.setValue(grid.rows)
        self.cols.setValue(grid.cols)

        self.page_size.setCurrentText(print_spec.page_size.upper())
        self.margin_mm.setValue(print_spec.margin_mm)
        self.spacing_mm.setValue(print_spec.spacing_mm)

    def _on_save_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu preset",
            "preset.json",
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            save_preset(path, self._current_template(), self._current_grid(), self._current_print())
        except Exception as e:
            QMessageBox.critical(self, "Lỗi preset", str(e))
            return
        QMessageBox.information(self, "OK", f"Đã lưu preset: {path}")

    def _on_generate_preview(self) -> None:
        seed_value = self.seed.value()
        seed = None if seed_value == 0 else seed_value
        numbers = generate_loto_15x6(seed=seed)

        template = self._current_template()
        grid = self._current_grid()

        img = render_ticket_preview(template, grid, numbers=numbers, scale=4.0)
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
            tickets.append(generate_loto_15x6(seed=seed))

        template = self._current_template()
        grid = self._current_grid()
        print_spec = self._current_print()

        try:
            export_tickets_a4_pdf(
                out_path=out_path,
                template=template,
                grid=grid,
                print_spec=print_spec,
                tickets=tickets,
                per_row=self.per_row.value(),
                per_col=self.per_col.value(),
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất PDF", str(e))
            return

        QMessageBox.information(self, "OK", f"Đã xuất PDF: {out_path}")
