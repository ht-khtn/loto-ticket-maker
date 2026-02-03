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


def _fit_font_size_for_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: float,
    max_size: int,
    min_size: int = 8,
) -> int:
    size = max(min_size, max_size)
    while size >= min_size:
        font = _get_font(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_w + 1e-6:
            return size
        size -= 1
    return min_size


def _fit_font_size_for_width_scaled(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: float,
    max_size: int,
    scale: float,
    ref_scale: float,
    min_size: int = 8,
) -> int:
    if scale <= 0:
        return min_size
    factor = ref_scale / scale
    size_ref = _fit_font_size_for_width(draw, text, max_w * factor, int(max_size * factor), min_size=min_size)
    return max(min_size, int(size_ref * scale / ref_scale))




def _draw_header(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec,
    seed: int | None,
    scale: float,
    ref_scale: float,
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
    # Draw header box with rounded corners
    radius = max(2, int(min(x2 - x1, y2 - y1) * 0.08))
    try:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, outline=(30, 41, 59), width=stroke_w)
    except Exception:
        draw.rectangle([x1, y1, x2, y2], outline=(30, 41, 59), width=stroke_w)

    inner_w = max(1.0, x2 - x1)
    inner_h = max(1.0, y2 - y1)
    gap = max(6.0, inner_w * 0.02)

    # Left: round_name + seed (nằm gần nhau, không bị ảnh hưởng tên đơn vị)
    left_col_w = inner_w * 0.34
    left_x = x1 + gap

    # Right: org_text / org_image (bên phải, tách riêng)
    right_col_w = inner_w - left_col_w - gap
    right_x = x1 + left_col_w + gap

    # LEFT COLUMN: Round Name (top) + Seed (below), centered
    available_h = inner_h - 2 * gap

    round_text = header.round_name
    round_font = None
    round_size = (0, 0)
    if round_text:
        round_font = _fit_font_for_text(
            draw,
            round_text,
            max_w=left_col_w - 2 * gap,
            max_h=available_h * 0.35,
            prefer_bold=True,
            min_size=10,
            max_size=int(available_h * 0.4),
        )
        bbox = draw.textbbox((0, 0), round_text, font=round_font)
        round_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])

    seed_text = None
    seed_font = None
    seed_size = (0, 0)
    if seed is not None:
        seed_text = str(seed)
        if header.seed_pad_length > 0:
            seed_text = seed_text.zfill(header.seed_pad_length)
        seed_font = _fit_font_for_text(
            draw,
            seed_text,
            max_w=left_col_w - 2 * gap,
            max_h=available_h * 0.55,
            prefer_bold=True,
            min_size=12,
            max_size=int(available_h * 0.6),
        )
        bbox = draw.textbbox((0, 0), seed_text, font=seed_font)
        seed_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])

    total_h = 0.0
    if round_text:
        total_h += round_size[1]
    if seed_text:
        total_h += seed_size[1]
    if round_text and seed_text:
        total_h += gap * 0.5
    start_y = y1 + (inner_h - total_h) / 2

    if round_text and round_font is not None:
        rx = left_x + (left_col_w - round_size[0]) / 2
        draw.text((rx, start_y), round_text, font=round_font, fill=(15, 23, 42))
        start_y += round_size[1] + gap * 0.5

    if seed_text and seed_font is not None:
        sx = left_x + (left_col_w - seed_size[0]) / 2
        sy = start_y
        # Dashed rounded border around seed
        pad = max(4.0, gap * 0.4)
        bbox = draw.textbbox((sx, sy), seed_text, font=seed_font)
        bx1 = bbox[0] - pad
        by1 = bbox[1] - pad * 0.2
        bx2 = bbox[2] + pad
        by2 = bbox[3] + pad * 1.1
        dash = max(4, int(pad * 0.8))
        gap_len = max(3, int(pad * 0.6))
        # draw dashed edges
        x = bx1 + radius
        while x < bx2 - radius:
            draw.line([(x, by1), (min(x + dash, bx2 - radius), by1)], fill=(59, 130, 246), width=stroke_w)
            draw.line([(x, by2), (min(x + dash, bx2 - radius), by2)], fill=(59, 130, 246), width=stroke_w)
            x += dash + gap_len
        y = by1 + radius
        while y < by2 - radius:
            draw.line([(bx1, y), (bx1, min(y + dash, by2 - radius))], fill=(59, 130, 246), width=stroke_w)
            draw.line([(bx2, y), (bx2, min(y + dash, by2 - radius))], fill=(59, 130, 246), width=stroke_w)
            y += dash + gap_len
        # corner arcs (solid to suggest rounding)
        try:
            draw.arc([bx1, by1, bx1 + 2 * radius, by1 + 2 * radius], 180, 270, fill=(59, 130, 246), width=stroke_w)
            draw.arc([bx2 - 2 * radius, by1, bx2, by1 + 2 * radius], 270, 360, fill=(59, 130, 246), width=stroke_w)
            draw.arc([bx1, by2 - 2 * radius, bx1 + 2 * radius, by2], 90, 180, fill=(59, 130, 246), width=stroke_w)
            draw.arc([bx2 - 2 * radius, by2 - 2 * radius, bx2, by2], 0, 90, fill=(59, 130, 246), width=stroke_w)
        except Exception:
            pass
        draw.text((sx, sy), seed_text, font=seed_font, fill=(59, 130, 246))

    # RIGHT COLUMN: Org image or org text (bên phải, tách riêng)
    right_y = y1 + gap
    right_h = inner_h - 2 * gap

    if header.org_image_path:
        try:
            org_img = Image.open(header.org_image_path).convert("RGBA")
            max_img_w = int(right_col_w - 2 * gap)
            max_img_h = int(right_h)
            if max_img_w > 0 and max_img_h > 0:
                org_img.thumbnail((max_img_w, max_img_h), Image.Resampling.LANCZOS)
                # Center image in the right column
                img_x = int(right_x + (right_col_w - org_img.width) * 0.5)
                img_y = int(right_y + (right_h - org_img.height) * 0.5)
                img.paste(org_img, (img_x, img_y), org_img)
        except Exception:
            pass
    else:
        # Org text (multiline, giữ nguyên khoảng trắng, canh giữa ngang + dọc)
        lines = header.org_text.splitlines() or [""]
        lines = lines[:6]
        max_w = right_col_w - 2 * gap

        # Compute per-line sizes based on width only (stable across zoom)
        sizes: list[int] = []
        max_size = int(right_h * 0.6)
        for line in lines:
            raw_line = line if line != "" else " "
            size = _fit_font_size_for_width_scaled(
                draw,
                raw_line,
                max_w,
                max_size,
                scale=scale,
                ref_scale=ref_scale,
                min_size=8,
            )
            sizes.append(size)

        total_text_h = sum(sizes)
        if len(sizes) > 1:
            remaining = max(0.0, right_h - total_text_h)
            min_size = min(sizes)
            gap_h = min(remaining / (len(sizes) - 1), min_size * 0.35)
        else:
            gap_h = 0.0
        total_h = total_text_h + gap_h * max(0, len(sizes) - 1)
        y = right_y + (right_h - total_h) / 2

        for line, size in zip(lines, sizes, strict=False):
            raw_line = line if line != "" else " "
            font = _get_font(size)
            bbox = draw.textbbox((0, 0), raw_line, font=font)
            tw = bbox[2] - bbox[0]
            tx = right_x + (right_col_w - tw) / 2
            draw.text((tx, y), raw_line, font=font, fill=(15, 23, 42))
            y += size + gap_h


def render_ticket_preview(
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec | None = None,
    numbers: list[list[int | None]] | None = None,
    seed: int | None = None,
    scale: float = 4.0,
    ref_scale: float | None = None,
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

    if ref_scale is None:
        ref_scale = scale

    if header is not None:
        _draw_header(img, draw, template, grid, header, seed=seed, scale=scale, ref_scale=ref_scale)

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
        font_size = max(10, int(min(cell_w_px, cell_h_px) * 0.55))
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
    ref_scale: float | None = None,
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
            ref_scale=(ref_scale or scale) * layout.scale,
        )
        img.paste(ticket_img, (x, y))

    return img
