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
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from ..core.grid_generator import generate_grid_rects_mm
from ..core.layout import compute_page_layout
from ..core.models import GridSpec, PrintSpec, TicketHeaderSpec, TicketTemplateSpec
from ..core.exceptions import LayoutError


def mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


@dataclass(frozen=True)
class PdfExportResult:
    path: str


def _page_mm_size(page_size: str) -> tuple[float, float]:
    name = page_size.upper().strip()
    if name == "A5":
        return 148.0, 210.0
    return 210.0, 297.0


def _fit_font_size(
    c: canvas.Canvas,
    text: str,
    font_name: str,
    max_w: float,
    max_h: float,
    min_size: int = 8,
    max_size: int = 48,
) -> int:
    if not text:
        return min_size
    size = max(min_size, min(max_size, int(max_h)))
    while size >= min_size:
        if c.stringWidth(text, font_name, size) <= max_w + 1e-6:
            return size
        size -= 1
    return min_size


def _draw_header(
    c: canvas.Canvas,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec,
    seed: Optional[int],
) -> None:
    header_h_mm = max(0.0, float(grid.header_height_mm))
    if header_h_mm <= 0:
        return

    ticket_w = mm_to_pt(template.width_mm)
    ticket_h = mm_to_pt(template.height_mm)
    pad = mm_to_pt(grid.padding_mm)

    x1 = pad
    x2 = ticket_w - pad
    y_top = ticket_h - pad
    y1 = y_top - mm_to_pt(header_h_mm)

    c.rect(x1, y1, x2 - x1, y_top - y1)

    inner_w = max(1.0, x2 - x1)
    inner_h = max(1.0, y_top - y1)
    gap = max(4.0, inner_w * 0.02)

    left_w = inner_w * 0.62
    right_w = inner_w - left_w

    left_x = x1 + gap
    right_x = x1 + left_w + gap

    # Left: org image or org text
    if header.org_image_path:
        try:
            c.drawImage(  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                ImageReader(header.org_image_path),
                left_x,
                y1 + gap,
                width=left_w - 2 * gap,
                height=inner_h - 2 * gap,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        except Exception:
            pass
    else:
        lines = [ln.strip() for ln in header.org_text.splitlines() if ln.strip()]
        if lines:
            per_line_h = (inner_h - 2 * gap) / max(1, len(lines))
            y = y_top - gap - per_line_h
            for line in lines[:6]:
                font_name = "Helvetica"
                size = _fit_font_size(
                    c,
                    line,
                    font_name=font_name,
                    max_w=left_w - 2 * gap,
                    max_h=per_line_h * 0.9,
                    min_size=8,
                    max_size=int(per_line_h * 1.2),
                )
                c.setFont(font_name, size)
                c.drawString(left_x, y + (per_line_h - size) * 0.2, line)
                y -= per_line_h

    # Right: round name + big seed
    round_text = header.round_name.strip()
    if round_text:
        font_name = "Helvetica-Bold"
        size = _fit_font_size(
            c,
            round_text,
            font_name=font_name,
            max_w=right_w - 2 * gap,
            max_h=inner_h * 0.35,
            min_size=10,
            max_size=int(inner_h * 0.35),
        )
        c.setFont(font_name, size)
        c.drawString(right_x, y_top - gap - size, round_text)

    if seed is not None:
        seed_text = str(seed)
        font_name = "Helvetica-Bold"
        size = _fit_font_size(
            c,
            seed_text,
            font_name=font_name,
            max_w=right_w - 2 * gap,
            max_h=inner_h * 0.55,
            min_size=14,
            max_size=int(inner_h * 0.7),
        )
        c.setFont(font_name, size)
        c.setFillColorRGB(0.01, 0.52, 0.78)
        c.drawString(right_x, y1 + gap, seed_text)
        c.setFillColorRGB(0, 0, 0)


def _draw_ticket_at_origin(
    c: canvas.Canvas,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec | None,
    numbers: Optional[list[list[Optional[int]]]] = None,
    seed: Optional[int] = None,
) -> None:
    """Vẽ 1 vé tại gốc (0,0) (góc dưới-trái của vé)."""
    ticket_w = mm_to_pt(template.width_mm)
    ticket_h = mm_to_pt(template.height_mm)

    if template.background_path:
        try:
            c.drawImage(  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                ImageReader(template.background_path),
                0,
                0,
                width=ticket_w,
                height=ticket_h,
                preserveAspectRatio=False,
                mask="auto",
            )
        except Exception:
            pass

    c.setLineWidth(max(0.25, mm_to_pt(grid.line_width_mm)))
    c.rect(0, 0, ticket_w, ticket_h)

    if header is not None:
        _draw_header(c, template, grid, header, seed)

    rects = generate_grid_rects_mm(template, grid)
    for rect in rects:
        x = mm_to_pt(rect.x)
        y = ticket_h - mm_to_pt(rect.y + rect.h)
        w = mm_to_pt(rect.w)
        h = mm_to_pt(rect.h)
        c.rect(x, y, w, h)

    if numbers is None:
        return

    # Font size theo chiều cao ô
    cell_h_pt = mm_to_pt(rects[0].h) if rects else mm_to_pt(8.0)
    font_size = max(8, min(28, int(cell_h_pt * float(grid.number_font_scale))))
    c.setFont("Helvetica-Bold", font_size)

    for r in range(min(grid.rows, len(numbers))):
        row = numbers[r]
        for col in range(min(grid.cols, len(row))):
            value = row[col]
            if value is None:
                continue
            rect = rects[r * grid.cols + col]
            x = mm_to_pt(rect.x)
            y = ticket_h - mm_to_pt(rect.y + rect.h)
            w = mm_to_pt(rect.w)
            h = mm_to_pt(rect.h)
            c.drawCentredString(x + w / 2, y + h / 2 - font_size * 0.35, str(value))


def _draw_ticket_scaled(
    c: canvas.Canvas,
    origin_x: float,
    origin_y: float,
    scale: float,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec | None,
    numbers: Optional[list[list[Optional[int]]]] = None,
    seed: Optional[int] = None,
) -> None:
    c.saveState()
    c.translate(origin_x, origin_y)
    c.scale(scale, scale)
    _draw_ticket_at_origin(c, template, grid, header, numbers=numbers, seed=seed)
    c.restoreState()


def export_tickets_pdf(
    out_path: str,
    template: TicketTemplateSpec,
    header: TicketHeaderSpec | None,
    grid: GridSpec,
    print_spec: PrintSpec,
    tickets: list[list[list[Optional[int]]]],
    seeds: list[Optional[int]] | None = None,
) -> PdfExportResult:
    """Xuất PDF theo mode trong PrintSpec.

    - mode="TICKET": mỗi vé = 1 trang, trang đúng kích thước vé
    - mode="PAGE": A4/A5, auto-fit N vé/trang theo tickets_per_page
    """

    mode = str(print_spec.mode).upper().strip()

    if mode == "TICKET":
        page_w = mm_to_pt(template.width_mm)
        page_h = mm_to_pt(template.height_mm)
        c = canvas.Canvas(out_path, pagesize=(page_w, page_h))
        for idx, numbers in enumerate(tickets):
            seed = seeds[idx] if seeds and idx < len(seeds) else None
            _draw_ticket_scaled(
                c,
                origin_x=0,
                origin_y=0,
                scale=1.0,
                template=template,
                grid=grid,
                header=header,
                numbers=numbers,
                seed=seed,
            )
            c.showPage()
        c.save()
        return PdfExportResult(path=out_path)

    # PAGE mode
    if print_spec.page_size.upper() == "A5":
        page_w, page_h = A5
    else:
        page_w, page_h = A4
    c = canvas.Canvas(out_path, pagesize=(page_w, page_h))

    page_w_mm, page_h_mm = _page_mm_size(print_spec.page_size)
    layout = compute_page_layout(
        page_w_mm=page_w_mm,
        page_h_mm=page_h_mm,
        ticket_w_mm=template.width_mm,
        ticket_h_mm=template.height_mm,
        margin_mm=print_spec.margin_mm,
        spacing_mm=print_spec.spacing_mm,
        tickets_per_page=print_spec.tickets_per_page,
    )

    margin = mm_to_pt(print_spec.margin_mm)
    spacing = mm_to_pt(print_spec.spacing_mm) * layout.scale

    ticket_w = mm_to_pt(template.width_mm) * layout.scale
    ticket_h = mm_to_pt(template.height_mm) * layout.scale

    avail_w = page_w - 2 * margin
    avail_h = page_h - 2 * margin
    need_w = layout.cols * ticket_w + max(0, layout.cols - 1) * spacing
    need_h = layout.rows * ticket_h + max(0, layout.rows - 1) * spacing
    if need_w > avail_w + 1e-6 or need_h > avail_h + 1e-6:
        raise LayoutError(
            "Không đủ chỗ trên trang với cấu hình hiện tại. "
            "Hãy giảm tickets_per_page, giảm kích thước vé, hoặc giảm lề/khoảng cách."
        )

    per_page = layout.rows * layout.cols
    for idx, numbers in enumerate(tickets):
        slot = idx % per_page
        if slot == 0 and idx != 0:
            c.showPage()

        r = slot // layout.cols
        col = slot % layout.cols
        origin_x = margin + col * (ticket_w + spacing)
        origin_y = page_h - margin - ticket_h - r * (ticket_h + spacing)
        seed = seeds[idx] if seeds and idx < len(seeds) else None
        _draw_ticket_scaled(
            c,
            origin_x=origin_x,
            origin_y=origin_y,
            scale=layout.scale,
            template=template,
            grid=grid,
            header=header,
            numbers=numbers,
            seed=seed,
        )

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
    """Backward-compatible wrapper (deprecated).

    Giữ API cũ để không vỡ import, nhưng sẽ redirect sang PAGE mode auto-fit.
    """
    _ = per_row
    _ = per_col
    print_spec2 = PrintSpec(
        mode="PAGE",
        page_size=print_spec.page_size,
        margin_mm=print_spec.margin_mm,
        spacing_mm=print_spec.spacing_mm,
        tickets_per_page=max(1, int(getattr(print_spec, "tickets_per_page", 6))),
    )
    return export_tickets_pdf(
        out_path=out_path,
        template=template,
        header=None,
        grid=grid,
        print_spec=print_spec2,
        tickets=tickets,
        seeds=None,
    )
