"""Xuất PDF để in.

Milestone đầu:
- xuất 1 trang với 1 vé (grid đơn giản)

Sau đó:
- nhiều vé/trang, canh lề, spacing
- chọn A4/A5/custom
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Optional

from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from ..core.layout import compute_page_layout
from ..core.models import GridSpec, PrintSpec, TicketHeaderSpec, TicketTemplateSpec
from ..core.exceptions import LayoutError
from ..render.ticket_renderer import render_ticket_preview


def mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


@dataclass(frozen=True)
class PdfExportResult:
    path: str


_PRINT_RENDER_SCALE = 8.0


def _page_mm_size(page_size: str, orientation: str) -> tuple[float, float]:
    name = page_size.upper().strip()
    w, h = (210.0, 297.0) if name != "A5" else (148.0, 210.0)
    if orientation.upper() == "LANDSCAPE":
        return h, w
    return w, h


def _draw_ticket_image(
    c: canvas.Canvas,
    origin_x: float,
    origin_y: float,
    width_pt: float,
    height_pt: float,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec | None,
    numbers: Optional[list[list[Optional[int]]]] = None,
    seed: Optional[int] = None,
    render_scale: float = _PRINT_RENDER_SCALE,
) -> None:
    img = render_ticket_preview(
        template=template,
        grid=grid,
        header=header,
        numbers=numbers,
        seed=seed,
        scale=render_scale,
        ref_scale=4.0,
    )
    c.drawImage(  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
        ImageReader(img),
        origin_x,
        origin_y,
        width=width_pt,
        height=height_pt,
        preserveAspectRatio=False,
        mask="auto",
    )


def export_tickets_pdf(
    out_path: str,
    template: TicketTemplateSpec,
    header: TicketHeaderSpec | None,
    grid: GridSpec,
    print_spec: PrintSpec,
    tickets: Iterable[list[list[Optional[int]]]],
    seeds: Iterable[Optional[int]] | None = None,
    total_tickets: int | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> PdfExportResult:
    """Xuất PDF theo mode trong PrintSpec.

    - mode="TICKET": mỗi vé = 1 trang, trang đúng kích thước vé
    - mode="PAGE": A4/A5, auto-fit N vé/trang theo tickets_per_page
    """

    mode = str(print_spec.mode).upper().strip()

    seeds_it: Iterator[Optional[int]] | None = iter(seeds) if seeds is not None else None

    if mode == "TICKET":
        page_w = mm_to_pt(template.width_mm)
        page_h = mm_to_pt(template.height_mm)
        c = canvas.Canvas(out_path, pagesize=(page_w, page_h))
        total_pages = max(1, int(total_tickets or 1))
        for idx, numbers in enumerate(tickets):
            seed = next(seeds_it) if seeds_it is not None else None
            _draw_ticket_image(
                c,
                origin_x=0,
                origin_y=0,
                width_pt=page_w,
                height_pt=page_h,
                template=template,
                grid=grid,
                header=header,
                numbers=numbers,
                seed=seed,
                render_scale=_PRINT_RENDER_SCALE,
            )
            c.showPage()
            if progress_cb is not None:
                progress_cb(idx + 1, total_pages)
        c.save()
        return PdfExportResult(path=out_path)

    # PAGE mode
    if print_spec.page_size.upper() == "A5":
        page_w, page_h = A5
    else:
        page_w, page_h = A4
    if print_spec.orientation.upper() == "LANDSCAPE":
        page_w, page_h = page_h, page_w
    c = canvas.Canvas(out_path, pagesize=(page_w, page_h))

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
    total_pages = (
        max(1, (int(total_tickets) + per_page - 1) // per_page)
        if total_tickets is not None
        else 1
    )
    last_page_index = -1
    for idx, numbers in enumerate(tickets):
        slot = idx % per_page
        if slot == 0 and idx != 0:
            c.showPage()
            if progress_cb is not None:
                progress_cb((idx // per_page), total_pages)

        r = slot // layout.cols
        col = slot % layout.cols
        origin_x = margin + col * (ticket_w + spacing)
        origin_y = page_h - margin - ticket_h - r * (ticket_h + spacing)
        seed = next(seeds_it) if seeds_it is not None else None
        _draw_ticket_image(
            c,
            origin_x=origin_x,
            origin_y=origin_y,
            width_pt=ticket_w,
            height_pt=ticket_h,
            template=template,
            grid=grid,
            header=header,
            numbers=numbers,
            seed=seed,
            render_scale=_PRINT_RENDER_SCALE * layout.scale,
        )
        last_page_index = max(last_page_index, idx // per_page)

    if total_tickets is None:
        total_pages = max(1, last_page_index + 1)
    c.showPage()
    if progress_cb is not None:
        progress_cb(total_pages, total_pages)
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
        total_tickets=len(tickets),
    )
