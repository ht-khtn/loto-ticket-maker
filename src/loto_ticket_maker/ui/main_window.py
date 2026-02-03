"""Màn hình chính.

Mục tiêu:
- Bên trái: nhóm tuỳ chọn (template, grid, in ấn)
- Bên phải: preview vé (zoom/pan sau)

Hiện tại chỉ là khung để bắt đầu nhanh.
"""

from __future__ import annotations

from pathlib import Path
import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
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
    QPushButton,
    QRadioButton,
    QScrollArea,
    QFileDialog,
    QVBoxLayout,
    QWidget,
)

from ..config.defaults import DEFAULT_GRID, DEFAULT_PRINT, DEFAULT_TEMPLATE
from ..config.presets import load_preset, save_preset
from ..core.loto_15x6 import generate_loto_15x6
from ..core.models import GridSpec, PrintSpec, TicketHeaderSpec, TicketTemplateSpec
from ..export.pdf_exporter import export_tickets_pdf
from ..render.ticket_renderer import render_page_preview, render_ticket_preview
from .image_utils import pil_to_qpixmap


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Loto Ticket Maker")
        self.resize(1200, 720)

        # Initialize early before any UI building
        self._background_path: str | None = DEFAULT_TEMPLATE.background_path
        self._org_image_path: str | None = None
        self._last_preview: QPixmap | None = None
        self._last_seed: int | None = None

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

        sidebar_layout.addWidget(self._build_preset_group(sidebar))
        sidebar_layout.addWidget(self._build_template_group(sidebar))
        sidebar_layout.addWidget(self._build_header_group(sidebar))
        sidebar_layout.addWidget(self._build_grid_group(sidebar))
        sidebar_layout.addWidget(self._build_print_group(sidebar))

        btn_generate = QPushButton("Tạo vé (preview)")
        btn_export = QPushButton("Xuất PDF")
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

    def _build_collapsible_group(self, title: str, parent: QWidget, expanded: bool = False) -> tuple[QGroupBox, QWidget]:
        box = QGroupBox(title, parent)
        box.setCheckable(True)
        box.setChecked(expanded)
        outer = QVBoxLayout(box)
        inner = QWidget(box)
        outer.addWidget(inner)

        def _on_toggled(checked: bool) -> None:
            inner.setVisible(checked)

        box.toggled.connect(_on_toggled)
        inner.setVisible(expanded)
        return box, inner

    def _build_preset_group(self, parent: QWidget) -> QGroupBox:
        box, inner = self._build_collapsible_group("Preset", parent, expanded=False)
        lay = QGridLayout(inner)

        btn_load = QPushButton("Mở preset…")
        btn_save = QPushButton("Lưu preset…")
        btn_sample = QPushButton("Nạp preset mẫu")
        btn_load.clicked.connect(self._on_load_preset)
        btn_save.clicked.connect(self._on_save_preset)
        btn_sample.clicked.connect(self._on_load_sample_preset)

        lay.addWidget(btn_load, 0, 0)
        lay.addWidget(btn_save, 0, 1)
        lay.addWidget(btn_sample, 1, 0, 1, 2)
        return box

    def _build_template_group(self, parent: QWidget) -> QGroupBox:
        box, inner = self._build_collapsible_group("Nền vé (template)", parent, expanded=False)
        lay = QGridLayout(inner)

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

        self._refresh_template_ui()
        return box

    def _build_header_group(self, parent: QWidget) -> QGroupBox:
        box, inner = self._build_collapsible_group("Header (thông tin trên vé)", parent, expanded=False)
        lay = QGridLayout(inner)

        lay.addWidget(QLabel("Đơn vị / tổ chức"), 0, 0, 1, 2)
        self.org_text = QPlainTextEdit()
        self.org_text.setPlaceholderText("Ví dụ:\nCÔNG TY ABC\nCHI NHÁNH 1")
        self.org_text.setFixedHeight(90)
        lay.addWidget(self.org_text, 1, 0, 1, 2)

        lay.addWidget(QLabel("Hoặc logo/ảnh"), 2, 0)
        self.org_image_label = QLabel("(không có)")
        self.org_image_label.setWordWrap(True)
        self.org_image_label.setStyleSheet("color: #93C5FD;")
        lay.addWidget(self.org_image_label, 2, 1)

        btn_org_img = QPushButton("Chọn ảnh…")
        btn_org_img_clear = QPushButton("Xoá")
        btn_org_img.clicked.connect(self._on_choose_org_image)
        btn_org_img_clear.clicked.connect(self._on_clear_org_image)
        lay.addWidget(btn_org_img, 3, 0)
        lay.addWidget(btn_org_img_clear, 3, 1)

        lay.addWidget(QLabel("Tên vòng"), 4, 0)
        self.round_name = QLineEdit()
        self.round_name.setPlaceholderText("Ví dụ: VÒNG 12")
        lay.addWidget(self.round_name, 4, 1)

        lay.addWidget(QLabel("Cỡ chữ số"), 5, 0)
        self.number_font_scale = QDoubleSpinBox()
        self.number_font_scale.setRange(0.35, 0.95)
        self.number_font_scale.setDecimals(2)
        self.number_font_scale.setSingleStep(0.05)
        self.number_font_scale.setValue(DEFAULT_GRID.number_font_scale)
        lay.addWidget(self.number_font_scale, 5, 1)

        return box

    def _build_grid_group(self, parent: QWidget) -> QGroupBox:
        box, inner = self._build_collapsible_group("Ô số (grid)", parent, expanded=False)
        lay = QGridLayout(inner)

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

        lay.addWidget(QLabel("Cao header (mm)"), 4, 0)
        self.header_height_mm = QDoubleSpinBox()
        self.header_height_mm.setRange(0.0, 60.0)
        self.header_height_mm.setDecimals(1)
        self.header_height_mm.setSingleStep(1.0)
        self.header_height_mm.setValue(DEFAULT_GRID.header_height_mm)
        lay.addWidget(self.header_height_mm, 4, 1)

        lay.addWidget(QLabel("Gap nhóm 3 hàng (mm)"), 5, 0)
        self.row_group_gap_mm = QDoubleSpinBox()
        self.row_group_gap_mm.setRange(0.0, 20.0)
        self.row_group_gap_mm.setDecimals(1)
        self.row_group_gap_mm.setSingleStep(0.5)
        self.row_group_gap_mm.setValue(DEFAULT_GRID.row_group_gap_mm)
        lay.addWidget(self.row_group_gap_mm, 5, 1)

        hint = QLabel(
            "Luật đang dùng: 15x6 (đủ 1..60, mỗi hàng 2 ô trống, trống theo cột 6-5-5-5-5-4)"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6B7280;")
        lay.addWidget(hint, 6, 0, 1, 2)
        return box

    def _build_print_group(self, parent: QWidget) -> QGroupBox:
        box, inner = self._build_collapsible_group("In ấn (PDF)", parent, expanded=False)
        lay = QGridLayout(inner)

        lay.addWidget(QLabel("Chế độ xuất"), 0, 0)
        mode_wrap = QWidget()
        mode_lay = QVBoxLayout(mode_wrap)
        mode_lay.setContentsMargins(0, 0, 0, 0)

        self.mode_page = QRadioButton("Xuất theo trang A4/A5 (auto-fit)")
        self.mode_ticket = QRadioButton("Xuất vé thường (mỗi vé 1 trang)")
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

        lay.addWidget(QLabel("Vé / trang"), 2, 0)
        self.tickets_per_page = QSpinBox()
        self.tickets_per_page.setRange(1, 40)
        self.tickets_per_page.setValue(DEFAULT_PRINT.tickets_per_page)
        lay.addWidget(self.tickets_per_page, 2, 1)

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

        note = QLabel("PAGE mode: auto-fit theo vé/trang. TICKET mode: mỗi vé 1 trang đúng kích thước vé.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #6B7280;")
        lay.addWidget(note, 5, 0, 1, 2)
        self._refresh_print_ui()
        return box

    def _refresh_print_ui(self) -> None:
        is_page = self.mode_page.isChecked()
        self.page_size.setEnabled(is_page)
        self.tickets_per_page.setEnabled(is_page)

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

    def _current_header(self) -> TicketHeaderSpec:
        return TicketHeaderSpec(
            org_text=str(self.org_text.toPlainText()),
            org_image_path=self._org_image_path,
            round_name=str(self.round_name.text()),
        )

    def _current_grid(self) -> GridSpec:
        return GridSpec(
            rows=int(self.rows.value()),
            cols=int(self.cols.value()),
            padding_mm=DEFAULT_GRID.padding_mm,
            line_width_mm=DEFAULT_GRID.line_width_mm,
            header_height_mm=float(self.header_height_mm.value()),
            row_group_size=DEFAULT_GRID.row_group_size,
            row_group_gap_mm=float(self.row_group_gap_mm.value()),
            number_font_scale=float(self.number_font_scale.value()),
        )

    def _current_print(self) -> PrintSpec:
        mode = "PAGE" if self.mode_page.isChecked() else "TICKET"
        return PrintSpec(
            mode=mode,
            page_size=str(self.page_size.currentText()),
            margin_mm=float(self.margin_mm.value()),
            spacing_mm=float(self.spacing_mm.value()),
            tickets_per_page=int(self.tickets_per_page.value()),
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

    def _on_choose_org_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn logo/ảnh đơn vị",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        self._org_image_path = path
        self.org_image_label.setText(path)

    def _on_clear_org_image(self) -> None:
        self._org_image_path = None
        self.org_image_label.setText("(không có)")

    def _on_load_sample_preset(self) -> None:
        sample_path = Path(__file__).resolve().parents[3] / "assets" / "presets" / "sample_preset.json"
        if not sample_path.exists():
            QMessageBox.warning(self, "Không tìm thấy", f"Không thấy preset mẫu: {sample_path}")
            return
        try:
            template, header, grid, print_spec = load_preset(str(sample_path))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi preset", str(e))
            return
        self._apply_loaded_preset(template, header, grid, print_spec)

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
            template, header, grid, print_spec = load_preset(path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi preset", str(e))
            return

        self._apply_loaded_preset(template, header, grid, print_spec)

    def _apply_loaded_preset(
        self,
        template: TicketTemplateSpec,
        header: TicketHeaderSpec,
        grid: GridSpec,
        print_spec: PrintSpec,
    ) -> None:
        self.template_w.setValue(template.width_mm)
        self.template_h.setValue(template.height_mm)
        self._background_path = template.background_path
        self._refresh_template_ui()

        self.org_text.setPlainText(header.org_text)
        self._org_image_path = header.org_image_path
        self.org_image_label.setText(header.org_image_path or "(không có)")
        self.round_name.setText(header.round_name)

        # Grid cố định 15x6 theo RULE.md
        self.rows.setValue(grid.rows)
        self.cols.setValue(grid.cols)
        self.header_height_mm.setValue(grid.header_height_mm)
        self.row_group_gap_mm.setValue(grid.row_group_gap_mm)
        self.number_font_scale.setValue(grid.number_font_scale)

        mode = str(print_spec.mode).upper()
        self.mode_ticket.setChecked(mode == "TICKET")
        self.mode_page.setChecked(mode != "TICKET")
        self.page_size.setCurrentText(str(print_spec.page_size).upper())
        self.margin_mm.setValue(print_spec.margin_mm)
        self.spacing_mm.setValue(print_spec.spacing_mm)
        self.tickets_per_page.setValue(print_spec.tickets_per_page)
        self._refresh_print_ui()

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
            save_preset(path, self._current_template(), self._current_header(), self._current_grid(), self._current_print())
        except Exception as e:
            QMessageBox.critical(self, "Lỗi preset", str(e))
            return
        QMessageBox.information(self, "OK", f"Đã lưu preset: {path}")

    def _on_generate_preview(self) -> None:
        seed_value = int(self.seed.value())
        base_seed = seed_value if seed_value != 0 else random.randint(1, 2_000_000_000)

        template = self._current_template()
        header = self._current_header()
        grid = self._current_grid()
        print_spec = self._current_print()

        if str(print_spec.mode).upper() == "PAGE":
            per_page = int(print_spec.tickets_per_page)
            count = min(int(self.ticket_count.value()), max(1, per_page))
            tickets: list[list[list[int | None]]] = []
            seeds: list[int | None] = []
            for i in range(count):
                s = base_seed + i
                seeds.append(s)
                tickets.append(generate_loto_15x6(seed=s))
            img = render_page_preview(
                print_spec=print_spec,
                template=template,
                grid=grid,
                header=header,
                tickets=tickets,
                seeds=seeds,
                scale=3.0,
            )
        else:
            numbers = generate_loto_15x6(seed=base_seed)
            img = render_ticket_preview(template, grid, header=header, numbers=numbers, seed=base_seed, scale=4.0)

        pix = pil_to_qpixmap(img)

        self._last_preview = pix
        self._last_seed = base_seed
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

        seed_value = int(self.seed.value())
        base_seed = seed_value if seed_value != 0 else random.randint(1, 2_000_000_000)
        count = int(self.ticket_count.value())

        tickets: list[list[list[int | None]]] = []
        seeds: list[int | None] = []
        for i in range(count):
            s = base_seed + i
            seeds.append(s)
            tickets.append(generate_loto_15x6(seed=s))

        template = self._current_template()
        header = self._current_header()
        grid = self._current_grid()
        print_spec = self._current_print()

        try:
            export_tickets_pdf(
                out_path=out_path,
                template=template,
                header=header,
                grid=grid,
                print_spec=print_spec,
                tickets=tickets,
                seeds=seeds,
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất PDF", str(e))
            return

        QMessageBox.information(self, "OK", f"Đã xuất PDF: {out_path}")
