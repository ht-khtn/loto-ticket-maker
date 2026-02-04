"""Màn hình chính.

Mục tiêu:
- Bên trái: nhóm tuỳ chọn (template, grid, in ấn)
- Bên phải: preview vé (zoom/pan sau)

Hiện tại chỉ là khung để bắt đầu nhanh.
"""

from __future__ import annotations

from pathlib import Path
import os
import sys
from typing import Mapping, cast
import random

from PyQt5.QtCore import Qt, QEvent, QTimer, QObject, QPoint, QRegularExpression
from PyQt5.QtGui import QPixmap, QMouseEvent, QFontDatabase, QRegularExpressionValidator
from PyQt5.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QSlider,
    QScrollArea,
    QFileDialog,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from ..config.defaults import DEFAULT_GRID, DEFAULT_HEADER, DEFAULT_PRINT, DEFAULT_TEMPLATE
from ..config.presets import load_preset, save_preset
from ..core.layout import compute_page_layout
from ..core.exceptions import ExportCanceled
from ..core.loto_15x6 import generate_loto_15x6
from ..core.models import GridSpec, PrintSpec, TicketHeaderSpec, TicketTemplateSpec
from ..core.ticket import compose_ticket_seed
from ..export.pdf_exporter import export_tickets_pdf
from ..render.ticket_renderer import render_page_preview, render_ticket_preview
from .image_utils import pil_to_qpixmap


def _page_mm_size(page_size: str, orientation: str) -> tuple[float, float]:
    name = str(page_size).upper().strip()
    w, h = (210.0, 297.0) if name != "A5" else (148.0, 210.0)
    if str(orientation).upper().strip() == "LANDSCAPE":
        return h, w
    return w, h


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Loto Ticket Maker — Vé 15x6")
        self.resize(1200, 720)

        # Initialize early before any UI building
        self._background_path: str | None = DEFAULT_TEMPLATE.background_path
        self._org_image_path: str | None = None
        self._last_preview: QPixmap | None = None
        self._last_seed: int | None = None
        self._last_seed_from_manual: bool = False
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(200)
        self._preview_timer.timeout.connect(self._update_preview)
        self._dragging_preview = False
        self._drag_start_pos: QPoint | None = None
        self._drag_start_scroll: tuple[int, int] | None = None
        self.preview_scroll: QScrollArea | None = None

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

        # Sidebar with 2 columns and scroll (2/3 of screen)
        sidebar_scroll = QScrollArea(root)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_inner = QWidget()
        sidebar_layout = QHBoxLayout(sidebar_inner)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(8)

        # Left column
        left_col = QWidget()
        left_col_layout = QVBoxLayout(left_col)
        left_col_layout.setContentsMargins(0, 0, 0, 0)
        left_col_layout.addWidget(self._build_preset_group(left_col))
        left_col_layout.addWidget(self._build_template_group(left_col))
        left_col_layout.addWidget(self._build_header_group(left_col))
        left_col_layout.addStretch(1)

        # Right column
        right_col = QWidget()
        right_col_layout = QVBoxLayout(right_col)
        right_col_layout.setContentsMargins(0, 0, 0, 0)
        right_col_layout.addWidget(self._build_grid_group(right_col))
        right_col_layout.addWidget(self._build_print_group(right_col))
        right_col_layout.addStretch(1)

        sidebar_layout.addWidget(left_col, 1)
        sidebar_layout.addWidget(right_col, 1)

        # Buttons (below columns)
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_export = QPushButton("Xuất PDF")
        btn_layout.addWidget(btn_export)
        btn_layout.addStretch(1)

        btn_export.clicked.connect(self._on_export_pdf)

        # Wrap sidebar content with buttons
        sidebar_outer = QWidget()
        sidebar_outer_layout = QVBoxLayout(sidebar_outer)
        sidebar_outer_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_outer_layout.addWidget(sidebar_scroll, 1)
        sidebar_outer_layout.addWidget(btn_container)

        sidebar_scroll.setWidget(sidebar_inner)
        layout.addWidget(sidebar_outer, 2)

        # Preview area (1/3 of screen)
        preview_container = QFrame(root)
        preview_container.setFrameShape(QFrame.StyledPanel)
        preview_container.setProperty("panel", True)
        preview_layout = QVBoxLayout(preview_container)

        title = QLabel("Xem trước")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        zoom_wrap = QWidget()
        zoom_layout = QHBoxLayout(zoom_wrap)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.addWidget(title)
        zoom_layout.addStretch(1)
        zoom_label = QLabel("Thu phóng")
        self.zoom_value = QLabel("100%")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(zoom_label)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_value)

        self.preview_label = QLabel("Xem trước sẽ tự cập nhật theo tuỳ chọn")
        self.preview_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.preview_label.setMinimumHeight(500)
        self.preview_label.setStyleSheet("background: #111827; border-radius: 10px;")

        page_nav = QWidget()
        page_nav_layout = QHBoxLayout(page_nav)
        page_nav_layout.setContentsMargins(0, 0, 0, 0)
        page_nav_layout.setSpacing(8)
        page_nav_layout.addStretch(1)
        page_nav_layout.addWidget(QLabel("Trang"))
        self.preview_page = QSpinBox()
        self.preview_page.setRange(1, 1)
        self.preview_page.setValue(1)
        self.preview_page.setFixedWidth(70)
        page_nav_layout.addWidget(self.preview_page)
        self.preview_page_total = QLabel("/ 1 trang")
        self.preview_page_total.setStyleSheet("color: #9CA3AF;")
        page_nav_layout.addWidget(self.preview_page_total)

        scroll = QScrollArea(preview_container)
        scroll.setWidgetResizable(False)
        scroll.setWidget(self.preview_label)
        scroll.viewport().installEventFilter(self)
        scroll.viewport().setMouseTracking(True)
        self.preview_label.setCursor(Qt.OpenHandCursor)
        self.preview_scroll = scroll

        preview_layout.addWidget(zoom_wrap)
        preview_layout.addWidget(page_nav)
        preview_layout.addWidget(scroll)

        layout.addWidget(preview_container, 1)

        self._connect_auto_preview()
        self._schedule_preview()

    def _refresh_preview_paging(self) -> tuple[int, int]:
        """Trả về (page_index_0_based, total_pages).

        - PAGE mode: total_pages = số trang sẽ xuất theo layout thật
        - TICKET mode: luôn 1 trang
        """
        print_spec = self._current_print()
        if str(print_spec.mode).upper().strip() != "PAGE":
            self.preview_page.setEnabled(False)
            self.preview_page.setRange(1, 1)
            self.preview_page.setValue(1)
            self.preview_page_total.setText("/ 1 trang")
            return 0, 1

        self.preview_page.setEnabled(True)

        page_w_mm, page_h_mm = _page_mm_size(print_spec.page_size, print_spec.orientation)
        template = self._current_template()
        layout = compute_page_layout(
            page_w_mm=page_w_mm,
            page_h_mm=page_h_mm,
            ticket_w_mm=template.width_mm,
            ticket_h_mm=template.height_mm,
            margin_mm=print_spec.margin_mm,
            spacing_mm=print_spec.spacing_mm,
            tickets_per_page=print_spec.tickets_per_page,
        )
        per_page = max(1, int(layout.rows) * int(layout.cols))
        total = max(1, (int(self.ticket_count.value()) + per_page - 1) // per_page)

        cur = int(self.preview_page.value())
        cur = max(1, min(cur, total))
        self.preview_page.blockSignals(True)
        try:
            self.preview_page.setRange(1, total)
            self.preview_page.setValue(cur)
        finally:
            self.preview_page.blockSignals(False)

        self.preview_page_total.setText(f"/ {total} trang")
        return cur - 1, total

    def _build_preset_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Mẫu cấu hình", parent)
        lay = QGridLayout(box)

        btn_load = QPushButton("Mở mẫu…")
        btn_save = QPushButton("Lưu mẫu…")
        btn_sample = QPushButton("Nạp mẫu có sẵn")
        btn_load.clicked.connect(self._on_load_preset)
        btn_save.clicked.connect(self._on_save_preset)
        btn_sample.clicked.connect(self._on_load_sample_preset)

        lay.addWidget(btn_load, 0, 0)
        lay.addWidget(btn_save, 0, 1)
        lay.addWidget(btn_sample, 1, 0, 1, 2)
        return box

    def _build_template_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Nền vé", parent)
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

        self.bg_label = QLabel("(chưa chọn)")
        self.bg_label.setWordWrap(True)
        self.bg_label.setStyleSheet("color: #93C5FD;")
        lay.addWidget(QLabel("Ảnh nền"), 2, 0)
        lay.addWidget(self.bg_label, 2, 1)

        btn_bg = QPushButton("Chọn ảnh…")
        btn_bg_clear = QPushButton("Xoá")
        btn_bg.clicked.connect(self._on_choose_background)
        btn_bg_clear.clicked.connect(self._on_clear_background)
        lay.addWidget(btn_bg, 3, 0)
        lay.addWidget(btn_bg_clear, 3, 1)

        self._refresh_template_ui()
        return box

    def _build_header_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Thông tin đầu vé", parent)
        lay = QGridLayout(box)

        lay.addWidget(QLabel("Tên vòng"), 0, 0)
        self.round_name = QLineEdit()
        self.round_name.setPlaceholderText("Ví dụ: VÒNG 12")
        lay.addWidget(self.round_name, 0, 1)

        lay.addWidget(QLabel("Mã vòng"), 1, 0)
        self.round_code = QLineEdit()
        self.round_code.setPlaceholderText("Ví dụ: A12")
        self.round_code.setMaxLength(32)
        self.round_code.setToolTip("Chỉ gồm A..Z và 0..9. Dùng để ghép vào seed vé.")
        self.round_code.setValidator(QRegularExpressionValidator(QRegularExpression("^[A-Za-z0-9]{0,32}$")))
        lay.addWidget(self.round_code, 1, 1)

        org_label = QLabel("Đơn vị / tổ chức")
        lay.addWidget(org_label, 2, 0, 1, 2)
        self.org_text = QPlainTextEdit()
        self.org_text.setPlaceholderText("Ví dụ:\nCÔNG TY ABC\nCHI NHÁNH 1")
        self.org_text.setFixedHeight(90)
        lay.addWidget(self.org_text, 3, 0, 1, 2)

        lay.addWidget(QLabel("Hoặc logo/ảnh"), 4, 0)
        self.org_image_label = QLabel("(chưa chọn)")
        self.org_image_label.setWordWrap(True)
        self.org_image_label.setStyleSheet("color: #93C5FD;")
        lay.addWidget(self.org_image_label, 4, 1)

        btn_org_img = QPushButton("Chọn ảnh…")
        btn_org_img_clear = QPushButton("Xoá")
        btn_org_img.clicked.connect(self._on_choose_org_image)
        btn_org_img_clear.clicked.connect(self._on_clear_org_image)
        lay.addWidget(btn_org_img, 5, 0)
        lay.addWidget(btn_org_img_clear, 5, 1)

        lay.addWidget(QLabel("Font chữ"), 6, 0)
        self.font_family = QComboBox()
        self.font_family.addItem("(mặc định)", "")
        families = sorted(QFontDatabase.families())
        for name in families:
            self.font_family.addItem(name, name)
        self._set_font_family(str(DEFAULT_HEADER.font_family))
        lay.addWidget(self.font_family, 6, 1)

        return box

    def _build_grid_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Bảng số (15×6)", parent)
        lay = QGridLayout(box)

        lay.addWidget(QLabel("Hàng × Cột"), 0, 0)
        row_wrap = QWidget()
        row_lay = QHBoxLayout(row_wrap)
        row_lay.setContentsMargins(0, 0, 0, 0)
        self.rows = QSpinBox()
        self.rows.setRange(15, 15)
        self.rows.setValue(15)
        self.rows.setEnabled(False)
        self.cols = QSpinBox()
        self.cols.setRange(6, 6)
        self.cols.setValue(6)
        self.cols.setEnabled(False)
        row_lay.addWidget(self.rows)
        row_lay.addWidget(QLabel("×"))
        row_lay.addWidget(self.cols)
        lay.addWidget(row_wrap, 0, 1)

        lay.addWidget(QLabel("Seed (tái tạo)"), 2, 0)
        self.seed = QSpinBox()
        self.seed.setRange(0, 2_000_000_000)
        self.seed.setValue(0)
        self.seed.setToolTip("0 = ngẫu nhiên; số khác 0 để tái tạo đúng vé")
        lay.addWidget(self.seed, 2, 1)

        hint = QLabel(
            "Luật đang dùng: 15x6 (đủ 1..60, mỗi hàng 2 ô trống, trống theo cột 6-5-5-5-5-4)"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6B7280;")
        lay.addWidget(hint, 3, 0, 1, 2)
        return box

    def _build_print_group(self, parent: QWidget) -> QGroupBox:
        box = QGroupBox("Xuất PDF", parent)
        lay = QGridLayout(box)

        lay.addWidget(QLabel("Kiểu xuất"), 0, 0)
        mode_wrap = QWidget()
        mode_lay = QVBoxLayout(mode_wrap)
        mode_lay.setContentsMargins(0, 0, 0, 0)

        self.mode_page = QRadioButton("Theo trang")
        self.mode_ticket = QRadioButton("Theo vé")
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.mode_page)
        self._mode_group.addButton(self.mode_ticket)
        self.mode_page.setChecked(str(DEFAULT_PRINT.mode).upper() != "TICKET")
        self.mode_ticket.setChecked(str(DEFAULT_PRINT.mode).upper() == "TICKET")
        self.mode_page.toggled.connect(self._refresh_print_ui)
        self.mode_ticket.toggled.connect(self._refresh_print_ui)

        mode_lay.addWidget(self.mode_page)
        mode_lay.addWidget(self.mode_ticket)
        lay.addWidget(mode_wrap, 0, 1)

        lay.addWidget(QLabel("Khổ giấy"), 1, 0)
        self.page_size = QComboBox()
        self.page_size.addItems(["A4", "A5"])
        self.page_size.setCurrentText(DEFAULT_PRINT.page_size.upper())
        lay.addWidget(self.page_size, 1, 1)

        lay.addWidget(QLabel("Hướng giấy"), 2, 0)
        self.page_orientation = QComboBox()
        self.page_orientation.addItem("Dọc", "PORTRAIT")
        self.page_orientation.addItem("Ngang", "LANDSCAPE")
        self._set_page_orientation(str(DEFAULT_PRINT.orientation))
        lay.addWidget(self.page_orientation, 2, 1)

        lay.addWidget(QLabel("Chiều cao khung đầu vé (mm)"), 3, 0)
        self.header_height_mm = QDoubleSpinBox()
        self.header_height_mm.setRange(0.0, 60.0)
        self.header_height_mm.setDecimals(1)
        self.header_height_mm.setSingleStep(1.0)
        self.header_height_mm.setValue(DEFAULT_GRID.header_height_mm)
        lay.addWidget(self.header_height_mm, 3, 1)

        lay.addWidget(QLabel("Khoảng cách khung đầu vé (mm)"), 4, 0)
        self.header_spacing_mm = QDoubleSpinBox()
        self.header_spacing_mm.setRange(0.0, 20.0)
        self.header_spacing_mm.setDecimals(1)
        self.header_spacing_mm.setSingleStep(0.5)
        self.header_spacing_mm.setValue(DEFAULT_GRID.header_spacing_mm)
        lay.addWidget(self.header_spacing_mm, 4, 1)

        lay.addWidget(QLabel("Khoảng cách nhóm 3 hàng (mm)"), 5, 0)
        self.row_group_gap_mm = QDoubleSpinBox()
        self.row_group_gap_mm.setRange(0.0, 20.0)
        self.row_group_gap_mm.setDecimals(1)
        self.row_group_gap_mm.setSingleStep(0.5)
        self.row_group_gap_mm.setValue(DEFAULT_GRID.row_group_gap_mm)
        lay.addWidget(self.row_group_gap_mm, 5, 1)

        lay.addWidget(QLabel("Số vé xuất"), 6, 0)
        self.ticket_count = QSpinBox()
        self.ticket_count.setRange(1, 10000)
        self.ticket_count.setValue(6)
        lay.addWidget(self.ticket_count, 6, 1)

        lay.addWidget(QLabel("Vé mỗi trang"), 7, 0)
        self.tickets_per_page = QSpinBox()
        self.tickets_per_page.setRange(1, 40)
        self.tickets_per_page.setValue(DEFAULT_PRINT.tickets_per_page)
        lay.addWidget(self.tickets_per_page, 7, 1)

        lay.addWidget(QLabel("Lề trang (mm)"), 8, 0)
        self.margin_mm = QDoubleSpinBox()
        self.margin_mm.setRange(0.0, 50.0)
        self.margin_mm.setDecimals(1)
        self.margin_mm.setSingleStep(1.0)
        self.margin_mm.setValue(DEFAULT_PRINT.margin_mm)
        lay.addWidget(self.margin_mm, 8, 1)

        lay.addWidget(QLabel("Khoảng cách giữa các vé (mm)"), 9, 0)
        self.spacing_mm = QDoubleSpinBox()
        self.spacing_mm.setRange(0.0, 50.0)
        self.spacing_mm.setDecimals(1)
        self.spacing_mm.setSingleStep(1.0)
        self.spacing_mm.setValue(DEFAULT_PRINT.spacing_mm)
        lay.addWidget(self.spacing_mm, 9, 1)

        lay.addWidget(QLabel("Chất lượng xuất"), 10, 0)
        self.export_quality = QComboBox()
        self.export_quality.addItem("Nhanh", "LOW")
        self.export_quality.addItem("Cân bằng", "MEDIUM")
        self.export_quality.addItem("Cao", "HIGH")
        self._set_export_quality(str(DEFAULT_PRINT.export_quality))
        lay.addWidget(self.export_quality, 10, 1)

        note = QLabel(
            "Theo trang: tự canh theo vé/trang. \nTheo vé: mỗi vé 1 trang đúng kích thước vé."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #6B7280;")
        lay.addWidget(note, 11, 0, 1, 2)
        self._refresh_print_ui()
        return box

    def _set_page_orientation(self, orientation: str) -> None:
        value = str(orientation).upper()
        for i in range(self.page_orientation.count()):
            if str(self.page_orientation.itemData(i)).upper() == value:
                self.page_orientation.setCurrentIndex(i)
                return
        self.page_orientation.setCurrentIndex(0)

    def _set_export_quality(self, quality: str) -> None:
        value = str(quality).upper()
        for i in range(self.export_quality.count()):
            if str(self.export_quality.itemData(i)).upper() == value:
                self.export_quality.setCurrentIndex(i)
                return
        self.export_quality.setCurrentIndex(1)

    def _set_font_family(self, family: str) -> None:
        value = str(family)
        for i in range(self.font_family.count()):
            if str(self.font_family.itemData(i)) == value:
                self.font_family.setCurrentIndex(i)
                return
        self.font_family.setCurrentIndex(0)

    def _refresh_print_ui(self) -> None:
        is_page = self.mode_page.isChecked()
        self.page_size.setEnabled(is_page)
        self.page_orientation.setEnabled(is_page)
        self.tickets_per_page.setEnabled(is_page)
        self.margin_mm.setEnabled(is_page)
        self.spacing_mm.setEnabled(is_page)

    def _refresh_template_ui(self) -> None:
        if self._background_path:
            self.bg_label.setText(self._background_path)
        else:
            self.bg_label.setText("(chưa chọn)")

    def _current_template(self) -> TicketTemplateSpec:
        return TicketTemplateSpec(
            width_mm=float(self.template_w.value()),
            height_mm=float(self.template_h.value()),
            background_path=self._background_path,
        )

    def _current_header(self) -> TicketHeaderSpec:
        return TicketHeaderSpec(
            org_text=str(self.org_text.toPlainText()),
            org_image_path=self._org_image_path,
            round_name=str(self.round_name.text()),
            round_code=str(self.round_code.text()).strip().upper(),
            seed_pad_length=0,
            font_family=str(self.font_family.currentData() or ""),
        )

    def _current_grid(self) -> GridSpec:
        return GridSpec(
            rows=int(self.rows.value()),
            cols=int(self.cols.value()),
            padding_mm=DEFAULT_GRID.padding_mm,
            line_width_mm=DEFAULT_GRID.line_width_mm,
            header_height_mm=float(self.header_height_mm.value()),
            header_spacing_mm=float(self.header_spacing_mm.value()),
            row_group_size=DEFAULT_GRID.row_group_size,
            row_group_gap_mm=float(self.row_group_gap_mm.value()),
        )

    def _current_print(self) -> PrintSpec:
        mode = "PAGE" if self.mode_page.isChecked() else "TICKET"
        orientation = str(self.page_orientation.currentData() or "PORTRAIT")
        export_quality = str(self.export_quality.currentData() or "MEDIUM")
        return PrintSpec(
            mode=mode,
            page_size=str(self.page_size.currentText()),
            orientation=orientation,
            margin_mm=float(self.margin_mm.value()),
            spacing_mm=float(self.spacing_mm.value()),
            tickets_per_page=int(self.tickets_per_page.value()),
            export_quality=export_quality,
        )

    def _on_choose_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh nền",
            "",
            "Hình ảnh (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        self._background_path = path
        self._refresh_template_ui()
        self._schedule_preview()

    def _on_clear_background(self) -> None:
        self._background_path = None
        self._refresh_template_ui()
        self._schedule_preview()

    def _on_choose_org_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn logo/ảnh đơn vị",
            "",
            "Hình ảnh (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        self._org_image_path = path
        self.org_image_label.setText(path)
        self._schedule_preview()

    def _on_clear_org_image(self) -> None:
        self._org_image_path = None
        self.org_image_label.setText("(chưa chọn)")
        self._schedule_preview()

    def _on_load_sample_preset(self) -> None:
        candidates: list[Path] = []

        meipass = getattr(sys, "_MEIPASS", None)
        if isinstance(meipass, str) and meipass.strip():
            candidates.append(Path(meipass) / "assets" / "presets" / "sample_preset.json")

        # Dev mode (run from source)
        candidates.append(Path(__file__).resolve().parents[3] / "assets" / "presets" / "sample_preset.json")

        sample_path = next((p for p in candidates if p.exists()), None)
        if sample_path is None:
            tried = "\n".join(str(p) for p in candidates) or "(no candidates)"
            QMessageBox.warning(self, "Không tìm thấy", f"Không thấy mẫu có sẵn. Đã thử:\n{tried}")
            return
        try:
            template, header, grid, print_spec, ui_state = load_preset(str(sample_path))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi mẫu cấu hình", str(e))
            return
        self._apply_loaded_preset(template, header, grid, print_spec, cast(dict[str, int], ui_state))

    def _on_load_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Mở mẫu cấu hình",
            "",
            "Tệp JSON (*.json)",
        )
        if not path:
            return

        try:
            template, header, grid, print_spec, ui_state = load_preset(path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi mẫu cấu hình", str(e))
            return

        self._apply_loaded_preset(template, header, grid, print_spec, cast(dict[str, int], ui_state))

    def _apply_loaded_preset(
        self,
        template: TicketTemplateSpec,
        header: TicketHeaderSpec,
        grid: GridSpec,
        print_spec: PrintSpec,
        ui_state: Mapping[str, int],
    ) -> None:
        self.template_w.setValue(template.width_mm)
        self.template_h.setValue(template.height_mm)
        self._background_path = template.background_path
        self._refresh_template_ui()

        self.org_text.setPlainText(header.org_text)
        self._org_image_path = header.org_image_path
        self.org_image_label.setText(header.org_image_path or "(chưa chọn)")
        self.round_name.setText(header.round_name)
        self.round_code.setText(getattr(header, "round_code", ""))
        self._set_font_family(header.font_family)

        # Grid cố định 15x6 theo RULE.md
        self.rows.setValue(grid.rows)
        self.cols.setValue(grid.cols)
        self.header_height_mm.setValue(grid.header_height_mm)
        self.header_spacing_mm.setValue(grid.header_spacing_mm)
        self.row_group_gap_mm.setValue(grid.row_group_gap_mm)

        self.seed.setValue(int(ui_state.get("seed", 0)))
        self.ticket_count.setValue(int(ui_state.get("ticket_count", 6)))

        mode = str(print_spec.mode).upper()
        self.mode_ticket.setChecked(mode == "TICKET")
        self.mode_page.setChecked(mode != "TICKET")
        self.page_size.setCurrentText(str(print_spec.page_size).upper())
        self._set_page_orientation(str(print_spec.orientation))
        self.margin_mm.setValue(print_spec.margin_mm)
        self.spacing_mm.setValue(print_spec.spacing_mm)
        self.tickets_per_page.setValue(print_spec.tickets_per_page)
        self._set_export_quality(str(print_spec.export_quality))
        self._refresh_print_ui()

    def _on_save_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu mẫu cấu hình",
            "preset.json",
            "Tệp JSON (*.json)",
        )
        if not path:
            return
        try:
            save_preset(
                path,
                self._current_template(),
                self._current_header(),
                self._current_grid(),
                self._current_print(),
                seed=int(self.seed.value()),
                ticket_count=int(self.ticket_count.value()),
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi mẫu cấu hình", str(e))
            return
        QMessageBox.information(self, "Thành công", f"Đã lưu mẫu cấu hình: {path}")

    def _connect_auto_preview(self) -> None:
        self.template_w.valueChanged.connect(self._schedule_preview)
        self.template_h.valueChanged.connect(self._schedule_preview)
        self.seed.valueChanged.connect(self._schedule_preview)
        self.ticket_count.valueChanged.connect(self._schedule_preview)
        self.header_height_mm.valueChanged.connect(self._schedule_preview)
        self.header_spacing_mm.valueChanged.connect(self._schedule_preview)
        self.page_size.currentTextChanged.connect(self._schedule_preview)
        self.page_orientation.currentTextChanged.connect(self._schedule_preview)
        self.tickets_per_page.valueChanged.connect(self._schedule_preview)
        self.margin_mm.valueChanged.connect(self._schedule_preview)
        self.spacing_mm.valueChanged.connect(self._schedule_preview)
        self.row_group_gap_mm.valueChanged.connect(self._schedule_preview)
        self.mode_page.toggled.connect(self._schedule_preview)
        self.mode_ticket.toggled.connect(self._schedule_preview)
        self.round_name.textChanged.connect(self._schedule_preview)
        self.round_code.textChanged.connect(self._on_round_code_changed)
        self.org_text.textChanged.connect(self._schedule_preview)
        self.font_family.currentTextChanged.connect(self._schedule_preview)
        self.preview_page.valueChanged.connect(self._schedule_preview)

    def _on_round_code_changed(self) -> None:
        raw = str(self.round_code.text() or "")
        upper = raw.upper()
        if raw != upper:
            self.round_code.blockSignals(True)
            self.round_code.setText(upper)
            self.round_code.blockSignals(False)
        self._schedule_preview()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            self.preview_scroll is not None
            and watched is self.preview_scroll.viewport()
            and isinstance(event, QMouseEvent)
        ):
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._dragging_preview = True
                    self._drag_start_pos = event.position().toPoint()
                    self._drag_start_scroll = (
                        self.preview_scroll.horizontalScrollBar().value(),
                        self.preview_scroll.verticalScrollBar().value(),
                    )
                    self.preview_label.setCursor(Qt.ClosedHandCursor)
                    return True
            elif event.type() == QEvent.Type.MouseMove and self._dragging_preview:
                if self._drag_start_pos and self._drag_start_scroll:
                    delta = event.position().toPoint() - self._drag_start_pos
                    self.preview_scroll.horizontalScrollBar().setValue(self._drag_start_scroll[0] - delta.x())
                    self.preview_scroll.verticalScrollBar().setValue(self._drag_start_scroll[1] - delta.y())
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self._dragging_preview:
                    self._dragging_preview = False
                    self._drag_start_pos = None
                    self._drag_start_scroll = None
                    self.preview_label.setCursor(Qt.OpenHandCursor)
                    return True
        return super().eventFilter(watched, event)

    def _schedule_preview(self) -> None:
        self._preview_timer.start()

    def _on_zoom_changed(self) -> None:
        self.zoom_value.setText(f"{self.zoom_slider.value()}%")
        self._schedule_preview()

    def _resolve_base_seed(self) -> int:
        seed_value = int(self.seed.value())
        if seed_value != 0:
            self._last_seed = seed_value
            self._last_seed_from_manual = True
            return seed_value
        # seed=0 => auto-random; nếu vừa đổi từ seed tay về 0 thì random lại.
        if self._last_seed is None or self._last_seed_from_manual:
            self._last_seed = random.randint(1, 2_000_000_000)
            self._last_seed_from_manual = False
        return self._last_seed

    def _update_preview(self) -> None:
        base_seed = self._resolve_base_seed()

        template = self._current_template()
        header = self._current_header()
        grid = self._current_grid()
        print_spec = self._current_print()
        zoom = self.zoom_slider.value() / 100.0
        render_zoom = max(1.0, zoom)

        page_index, _total_pages = self._refresh_preview_paging()

        if str(print_spec.mode).upper() == "PAGE":
            page_w_mm, page_h_mm = _page_mm_size(print_spec.page_size, print_spec.orientation)
            layout = compute_page_layout(
                page_w_mm=page_w_mm,
                page_h_mm=page_h_mm,
                ticket_w_mm=template.width_mm,
                ticket_h_mm=template.height_mm,
                margin_mm=print_spec.margin_mm,
                spacing_mm=print_spec.spacing_mm,
                tickets_per_page=print_spec.tickets_per_page,
            )
            per_page = max(1, int(layout.rows) * int(layout.cols))

            total_tickets = int(self.ticket_count.value())
            start = page_index * per_page
            end = min(total_tickets, start + per_page)
            count = max(0, end - start)
            tickets: list[list[list[int | None]]] = []
            seeds: list[int | None] = []
            for i in range(count):
                base = base_seed + (start + i)
                effective = compose_ticket_seed(header.round_code, base)
                seeds.append(effective)
                tickets.append(generate_loto_15x6(seed=effective))
            img = render_page_preview(
                print_spec=print_spec,
                template=template,
                grid=grid,
                header=header,
                tickets=tickets,
                seeds=seeds,
                scale=3.0 * render_zoom,
                ref_scale=3.0,
            )
        else:
            effective_seed = compose_ticket_seed(header.round_code, base_seed)
            numbers = generate_loto_15x6(seed=effective_seed)
            img = render_ticket_preview(
                template,
                grid,
                header=header,
                numbers=numbers,
                seed=effective_seed,
                scale=4.0 * render_zoom,
                ref_scale=4.0,
            )

        pix = pil_to_qpixmap(img)

        self._last_preview = pix
        self._last_seed = base_seed
        if zoom < 1.0:
            target_w = max(1, int(pix.width() * zoom))
            target_h = max(1, int(pix.height() * zoom))
            pix = pix.scaled(
                target_w,
                target_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        self.preview_label.setPixmap(pix)
        self.preview_label.resize(pix.size())

    def _on_export_pdf(self) -> None:
        self._update_preview()
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Xuất PDF",
            "loto_tickets_a4.pdf",
            "Tệp PDF (*.pdf)",
        )
        if not out_path:
            return

        base_seed = self._resolve_base_seed()
        count = int(self.ticket_count.value())

        template = self._current_template()
        header = self._current_header()
        grid = self._current_grid()
        print_spec = self._current_print()

        seeds_list = [compose_ticket_seed(header.round_code, base_seed + i) for i in range(count)]
        tickets = (generate_loto_15x6(seed=s) for s in seeds_list)
        seeds = seeds_list

        total_pages = 1
        if str(print_spec.mode).upper() == "TICKET":
            total_pages = max(1, count)
        else:
            page_w_mm, page_h_mm = _page_mm_size(print_spec.page_size, print_spec.orientation)
            layout = compute_page_layout(
                page_w_mm=page_w_mm,
                page_h_mm=page_h_mm,
                ticket_w_mm=template.width_mm,
                ticket_h_mm=template.height_mm,
                margin_mm=print_spec.margin_mm,
                spacing_mm=print_spec.spacing_mm,
                tickets_per_page=print_spec.tickets_per_page,
            )
            per_page = max(1, int(layout.rows) * int(layout.cols))
            total_pages = max(1, (count + per_page - 1) // per_page)

        progress = QProgressDialog(
            f"Đang xuất trang 0/{total_pages}",
            "Hủy",
            0,
            total_pages,
            self,
        )
        progress.setWindowTitle("Đang xuất PDF")
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        canceled = {"value": False}

        def _on_cancel() -> None:
            canceled["value"] = True

        progress.canceled.connect(_on_cancel)

        def _on_progress(current: int, total: int) -> None:
            progress.setLabelText(f"Đang xuất trang {current}/{total}")
            progress.setMaximum(total)
            progress.setValue(current)
            QApplication.processEvents()

        def _is_canceled() -> bool:
            return bool(canceled["value"])

        try:
            export_tickets_pdf(
                out_path=out_path,
                template=template,
                header=header,
                grid=grid,
                print_spec=print_spec,
                tickets=tickets,
                seeds=seeds,
                total_tickets=count,
                progress_cb=_on_progress,
                cancel_cb=_is_canceled,
            )
        except ExportCanceled:
            progress.close()
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except Exception:
                pass
            QMessageBox.information(self, "Đã hủy", "Đã hủy xuất PDF theo yêu cầu.")
            return
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Lỗi xuất PDF", str(e))
            return

        progress.close()

        QMessageBox.information(self, "Thành công", f"Đã xuất PDF: {out_path}")
