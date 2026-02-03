"""Render vé sang ảnh để preview trong GUI.

Milestone đầu có thể:
- tạo ảnh nền trắng
- vẽ grid (line)

Sau đó:
- chèn background image
- vẽ số, font, style
"""

from __future__ import annotations

from typing import cast

from PIL import Image, ImageDraw, ImageFont

from ..core.grid_generator import generate_grid_rects_mm
from ..core.layout import compute_page_layout
from ..core.models import GridSpec, PrintSpec, TicketHeaderSpec, TicketTemplateSpec


def _get_font(size_px: int) -> ImageFont.ImageFont:
    # Ưu tiên font phổ biến trên Windows; fallback về default.
    for name in ("arialbd.ttf", "arial.ttf"):
        try:
            return cast(ImageFont.ImageFont, ImageFont.truetype(name, size_px))
        except OSError:
            pass
    return cast(ImageFont.ImageFont, ImageFont.load_default())


def _fit_font_for_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: float,
    max_h: float,
    prefer_bold: bool,
    min_size: int = 8,
    max_size: int = 72,
) -> ImageFont.ImageFont:
    if not text:
        return _get_font(min_size)

    max_size = max(min_size, max_size)
    size = min(max_size, max(min_size, int(max_h)))
    while size >= min_size:
        font = _get_font(size) if not prefer_bold else _get_font(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_w + 1e-6 and h <= max_h + 1e-6:
            return font
        size -= 1
    return _get_font(min_size)


def _draw_header(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec,
    seed: int | None,
    scale: float,
) -> None:
    header_h_mm = max(0.0, float(grid.header_height_mm))
    if header_h_mm <= 0:
        return

    pad_px = grid.padding_mm * scale
    x1 = pad_px
    y1 = pad_px
    x2 = (template.width_mm - grid.padding_mm) * scale
    y2 = (grid.padding_mm + header_h_mm) * scale

    stroke_w = max(1, int(grid.line_width_mm * scale))
    draw.rectangle([x1, y1, x2, y2], outline=(30, 41, 59), width=stroke_w)

    inner_w = max(1.0, x2 - x1)
    inner_h = max(1.0, y2 - y1)

    left_w = inner_w * 0.62
    right_w = inner_w - left_w
    gap = max(6.0, inner_w * 0.02)

    left_x = x1 + gap
    left_y = y1 + gap
    right_x = x1 + left_w + gap
    right_y = y1 + gap

    # Org image (optional)
    if header.org_image_path:
        try:
            org_img = Image.open(header.org_image_path).convert("RGBA")
            max_img_w = int(left_w - 2 * gap)
            max_img_h = int(inner_h - 2 * gap)
            if max_img_w > 0 and max_img_h > 0:
                org_img.thumbnail((max_img_w, max_img_h))
                img.paste(org_img, (int(left_x), int(left_y)), org_img)
        except Exception:
            pass
    else:
        # Org text (multiline, auto-fit per line)
        lines = [ln.strip() for ln in header.org_text.splitlines() if ln.strip()]
        if lines:
            per_line_h = (inner_h - 2 * gap) / max(1, len(lines))
            y = left_y
            for line in lines[:6]:
                font = _fit_font_for_text(
                    draw,
                    line,
                    max_w=left_w - 2 * gap,
                    max_h=per_line_h * 0.9,
                    prefer_bold=False,
                    min_size=8,
                    max_size=int(per_line_h * 1.2),
                )
                draw.text((left_x, y), line, font=font, fill=(15, 23, 42))
                y += per_line_h

    # Right: round name + big seed
    round_text = header.round_name.strip()
    if round_text:
        font = _fit_font_for_text(
            draw,
            round_text,
            max_w=right_w - 2 * gap,
            max_h=inner_h * 0.35,
            prefer_bold=True,
            min_size=10,
            max_size=int(inner_h * 0.35),
        )
        draw.text((right_x, right_y), round_text, font=font, fill=(15, 23, 42))

    if seed is not None:
        seed_text = str(seed)
        font = _fit_font_for_text(
            draw,
            seed_text,
            max_w=right_w - 2 * gap,
            max_h=inner_h * 0.55,
            prefer_bold=True,
            min_size=14,
            max_size=int(inner_h * 0.7),
        )
        bbox = draw.textbbox((0, 0), seed_text, font=font)
        th = bbox[3] - bbox[1]
        draw.text((right_x, y2 - gap - th), seed_text, font=font, fill=(2, 132, 199))


def render_ticket_preview(
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec | None = None,
    numbers: list[list[int | None]] | None = None,
    seed: int | None = None,
    scale: float = 4.0,
) -> Image.Image:
    """Render vé ra ảnh PIL.

    `scale` = số pixel cho mỗi mm (xấp xỉ). Dùng cho preview, không dùng cho in.
    """
    width_px = max(1, int(template.width_mm * scale))
    height_px = max(1, int(template.height_mm * scale))

    img = Image.new("RGB", (width_px, height_px), (255, 255, 255))
    if template.background_path:
        try:
            bg = Image.open(template.background_path).convert("RGB")
            resample_filter = int(Image.Resampling.LANCZOS)  # type: ignore[reportUnknownMemberType]
            bg = bg.resize((width_px, height_px), resample_filter)  # type: ignore[reportUnknownArgumentType]
            img.paste(bg, (0, 0))
        except Exception:
            pass
    draw = ImageDraw.Draw(img)

    # ticket border
    draw.rectangle(
        [0, 0, width_px - 1, height_px - 1],
        outline=(30, 41, 59),
        width=max(1, int(grid.line_width_mm * scale)),
    )

    if header is not None:
        _draw_header(img, draw, template, grid, header, seed=seed, scale=scale)

    rects = generate_grid_rects_mm(template, grid)
    stroke_w = max(1, int(grid.line_width_mm * scale))
    for rect in rects:
        x1 = rect.x * scale
        y1 = rect.y * scale
        x2 = (rect.x + rect.w) * scale
        y2 = (rect.y + rect.h) * scale
        draw.rectangle([x1, y1, x2, y2], outline=(30, 41, 59), width=stroke_w)

    if numbers is not None:
        # Vẽ số vào giữa ô
        first = rects[0] if rects else None
        cell_w_px = (first.w * scale) if first else 40.0
        cell_h_px = (first.h * scale) if first else 40.0
        font_size = max(10, int(min(cell_w_px, cell_h_px) * float(grid.number_font_scale)))
        font = _get_font(font_size)

        for r in range(min(grid.rows, len(numbers))):
            row = numbers[r]
            for c in range(min(grid.cols, len(row))):
                value = row[c]
                if value is None:
                    continue

                rect = rects[r * grid.cols + c]
                cx = (rect.x + rect.w / 2) * scale
                cy = (rect.y + rect.h / 2) * scale
                text = str(value)

                # PIL text centering
                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                draw.text(
                    (cx - tw / 2, cy - th / 2),
                    text,
                    font=font,
                    fill=(15, 23, 42),
                )

    return img


def render_page_preview(
    print_spec: PrintSpec,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec | None,
    tickets: list[list[list[int | None]]],
    seeds: list[int | None] | None = None,
    scale: float = 3.0,
) -> Image.Image:
    page = print_spec.page_size.upper()
    if page == "A5":
        page_w_mm, page_h_mm = 148.0, 210.0
    else:
        page_w_mm, page_h_mm = 210.0, 297.0

    page_w_px = max(1, int(page_w_mm * scale))
    page_h_px = max(1, int(page_h_mm * scale))
    img = Image.new("RGB", (page_w_px, page_h_px), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, page_w_px - 1, page_h_px - 1], outline=(148, 163, 184), width=1)

    layout = compute_page_layout(
        page_w_mm=page_w_mm,
        page_h_mm=page_h_mm,
        ticket_w_mm=template.width_mm,
        ticket_h_mm=template.height_mm,
        margin_mm=print_spec.margin_mm,
        spacing_mm=print_spec.spacing_mm,
        tickets_per_page=print_spec.tickets_per_page,
    )

    margin_px = print_spec.margin_mm * scale
    spacing_px = print_spec.spacing_mm * scale * layout.scale
    tw_px = template.width_mm * scale * layout.scale
    th_px = template.height_mm * scale * layout.scale

    count = min(len(tickets), layout.rows * layout.cols)
    for idx in range(count):
        r = idx // layout.cols
        c = idx % layout.cols
        x = int(margin_px + c * (tw_px + spacing_px))
        y = int(margin_px + r * (th_px + spacing_px))

        seed = seeds[idx] if seeds and idx < len(seeds) else None
        ticket_img = render_ticket_preview(
            template=template,
            grid=grid,
            header=header,
            numbers=tickets[idx],
            seed=seed,
            scale=scale * layout.scale,
        )
        img.paste(ticket_img, (x, y))

    return img
