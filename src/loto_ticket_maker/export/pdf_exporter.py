"""Xuất PDF để in.

Milestone đầu:
- xuất 1 trang với 1 vé (grid đơn giản)

Sau đó:
- nhiều vé/trang, canh lề, spacing
- chọn A4/A5/custom
"""

from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib.pagesizes import A4, A5
from reportlab.pdfgen import canvas

from ..core.models import GridSpec, PrintSpec, TicketTemplateSpec
from ..core.grid_generator import generate_grid_rects_mm


def mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


@dataclass(frozen=True)
class PdfExportResult:
    path: str


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

    # vẽ khung vé
    c.rect(origin_x, origin_y, ticket_w, ticket_h)

    # vẽ grid
    rects = generate_grid_rects_mm(template, grid)
    for rect in rects:
        x = origin_x + mm_to_pt(rect.x)
        y = origin_y + ticket_h - mm_to_pt(rect.y + rect.h)
        w = mm_to_pt(rect.w)
        h = mm_to_pt(rect.h)
        c.rect(x, y, w, h)

    c.showPage()
    c.save()
    return PdfExportResult(path=out_path)
