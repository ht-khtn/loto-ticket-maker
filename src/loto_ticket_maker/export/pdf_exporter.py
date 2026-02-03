"""Xuất PDF để in.

Milestone đầu:
- xuất 1 trang với 1 vé (grid đơn giản)

Sau đó:
- nhiều vé/trang, canh lề, spacing
- chọn A4/A5/custom
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from reportlab.lib.pagesizes import A4, A5
from reportlab.pdfgen import canvas

from ..core.models import GridSpec, PrintSpec, TicketTemplateSpec
from ..core.grid_generator import generate_grid_rects_mm
from ..core.exceptions import LayoutError


def mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


@dataclass(frozen=True)
class PdfExportResult:
    path: str


def _draw_ticket(
    c: canvas.Canvas,
    origin_x: float,
    origin_y: float,
    template: TicketTemplateSpec,
    grid: GridSpec,
    numbers: Optional[list[list[Optional[int]]]] = None,
) -> None:
    """Vẽ 1 vé tại (origin_x, origin_y) (góc dưới-trái của vé)"""
    ticket_w = mm_to_pt(template.width_mm)
    ticket_h = mm_to_pt(template.height_mm)

    c.rect(origin_x, origin_y, ticket_w, ticket_h)

    rects = generate_grid_rects_mm(template, grid)
    for rect in rects:
        x = origin_x + mm_to_pt(rect.x)
        y = origin_y + ticket_h - mm_to_pt(rect.y + rect.h)
        w = mm_to_pt(rect.w)
        h = mm_to_pt(rect.h)
        c.rect(x, y, w, h)

    if numbers is None:
        return

    # Font size theo chiều cao ô
    cell_h_pt = mm_to_pt((template.height_mm - 2 * grid.padding_mm) / grid.rows)
    font_size = max(8, min(22, int(cell_h_pt * 0.45)))
    c.setFont("Helvetica-Bold", font_size)

    for r in range(min(grid.rows, len(numbers))):
        row = numbers[r]
        for col in range(min(grid.cols, len(row))):
            value = row[col]
            if value is None:
                continue
            rect = rects[r * grid.cols + col]
            x = origin_x + mm_to_pt(rect.x)
            y = origin_y + ticket_h - mm_to_pt(rect.y + rect.h)
            w = mm_to_pt(rect.w)
            h = mm_to_pt(rect.h)
            c.drawCentredString(x + w / 2, y + h / 2 - font_size * 0.35, str(value))


def export_single_ticket_pdf(
    out_path: str,
    template: TicketTemplateSpec,
    grid: GridSpec,
    print_spec: PrintSpec,
) -> PdfExportResult:
    if print_spec.page_size.upper() == "A5":
        page_w, page_h = A5
    else:
        page_w, page_h = A4

    c = canvas.Canvas(out_path, pagesize=(page_w, page_h))

    margin = mm_to_pt(print_spec.margin_mm)
    ticket_w = mm_to_pt(template.width_mm)
    ticket_h = mm_to_pt(template.height_mm)

    origin_x = margin
    origin_y = page_h - margin - ticket_h  # reportlab gốc ở góc dưới-trái

    _draw_ticket(c, origin_x, origin_y, template, grid, numbers=None)

    c.showPage()
    c.save()
    return PdfExportResult(path=out_path)


def export_tickets_a4_pdf(
    out_path: str,
    template: TicketTemplateSpec,
    grid: GridSpec,
    print_spec: PrintSpec,
    tickets: list[list[list[Optional[int]]]],
    per_row: int,
    per_col: int,
) -> PdfExportResult:
    """Xuất nhiều vé lên giấy A4 theo lưới per_row x per_col.

    Vé được giữ đúng kích thước vật lý (mm). Nếu không đủ chỗ sẽ báo lỗi.
    """
    page_w, page_h = A4
    c = canvas.Canvas(out_path, pagesize=(page_w, page_h))

    margin = mm_to_pt(print_spec.margin_mm)
    spacing = mm_to_pt(print_spec.spacing_mm)

    ticket_w = mm_to_pt(template.width_mm)
    ticket_h = mm_to_pt(template.height_mm)

    avail_w = page_w - 2 * margin
    avail_h = page_h - 2 * margin

    need_w = per_row * ticket_w + max(0, per_row - 1) * spacing
    need_h = per_col * ticket_h + max(0, per_col - 1) * spacing

    if need_w > avail_w + 1e-6 or need_h > avail_h + 1e-6:
        raise LayoutError(
            "Không đủ chỗ trên A4 với cấu hình hiện tại. "
            "Hãy giảm số vé/trang, giảm kích thước vé, hoặc giảm lề/khoảng cách."
        )

    per_page = per_row * per_col
    for idx, numbers in enumerate(tickets):
        slot = idx % per_page
        if slot == 0 and idx != 0:
            c.showPage()

        row = slot // per_row
        col = slot % per_row

        origin_x = margin + col * (ticket_w + spacing)
        origin_y = page_h - margin - ticket_h - row * (ticket_h + spacing)
        _draw_ticket(c, origin_x, origin_y, template, grid, numbers=numbers)

    c.showPage()
    c.save()
    return PdfExportResult(path=out_path)
