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
import os

from PIL import Image, ImageDraw, ImageFont

from ..core.grid_generator import RectMM, generate_grid_rects_mm
from ..core.layout import compute_page_layout
from ..core.models import GridSpec, PrintSpec, TicketHeaderSpec, TicketTemplateSpec

_BG_CACHE: dict[tuple[str, int, int], Image.Image] = {}
_ORG_IMAGE_CACHE: dict[str, Image.Image] = {}
_ORG_THUMB_CACHE: dict[tuple[str, int, int], Image.Image] = {}
_RECTS_CACHE: dict[tuple[float, float, int, int, float, float, float, float, int, float], list[RectMM]] = {}
_HEADER_BASE_CACHE: dict[
    tuple[
        float,
        float,
        float,
        float,
        float,
        float,
        int,
        float,
        float,
        float,
        str,
        str,
        str,
        str,
    ],
    Image.Image,
] = {}
_FONT_PATH_CACHE: dict[str, str] = {}
_FONT_OBJ_CACHE: dict[tuple[str, int], ImageFont.ImageFont] = {}
_font_indexed = False


def _get_cached_bg(path: str, width_px: int, height_px: int) -> Image.Image | None:
    key = (path, width_px, height_px)
    cached = _BG_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        bg = Image.open(path).convert("RGB")
        bg = bg.resize((width_px, height_px), cast(int, Image.Resampling.LANCZOS))  # pyright: ignore[reportUnknownMemberType]
        _BG_CACHE[key] = bg
        return bg
    except Exception:
        return None


def _get_cached_org_image(path: str) -> Image.Image | None:
    cached = _ORG_IMAGE_CACHE.get(path)
    if cached is not None:
        return cached
    try:
        img = Image.open(path).convert("RGBA")
        _ORG_IMAGE_CACHE[path] = img
        return img
    except Exception:
        return None


def _get_cached_org_thumb(path: str, max_w: int, max_h: int) -> Image.Image | None:
    if max_w <= 0 or max_h <= 0:
        return None
    key = (path, max_w, max_h)
    cached = _ORG_THUMB_CACHE.get(key)
    if cached is not None:
        return cached
    base = _get_cached_org_image(path)
    if base is None:
        return None
    img = base.copy()
    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    _ORG_THUMB_CACHE[key] = img
    return img


def _get_cached_rects(template: TicketTemplateSpec, grid: GridSpec) -> list[RectMM]:
    key = (
        float(template.width_mm),
        float(template.height_mm),
        int(grid.rows),
        int(grid.cols),
        float(grid.padding_mm),
        float(grid.line_width_mm),
        float(grid.header_height_mm),
        float(grid.header_spacing_mm),
        int(grid.row_group_size),
        float(grid.row_group_gap_mm),
    )
    cached = _RECTS_CACHE.get(key)
    if cached is not None:
        return cached
    rects = generate_grid_rects_mm(template, grid)
    _RECTS_CACHE[key] = rects
    return rects


def _build_font_cache() -> None:
    global _font_indexed
    if _font_indexed:
        return
    _font_indexed = True
    windir = os.environ.get("WINDIR", r"C:\\Windows")
    fonts_dir = os.path.join(windir, "Fonts")
    if not os.path.isdir(fonts_dir):
        return
    for name in os.listdir(fonts_dir):
        if not name.lower().endswith((".ttf", ".otf")):
            continue
        path = os.path.join(fonts_dir, name)
        try:
            font = ImageFont.truetype(path, 12)
            family = font.getname()[0]
            if family and family not in _FONT_PATH_CACHE:
                _FONT_PATH_CACHE[family] = path
        except Exception:
            continue


def _resolve_font_path(family: str) -> str | None:
    if not family:
        return None
    if os.path.isfile(family):
        return family
    _build_font_cache()
    return _FONT_PATH_CACHE.get(family)


def _get_font(size_px: int, family: str | None = None) -> ImageFont.ImageFont:
    # Ưu tiên font phổ biến trên Windows; fallback về default.
    fam = family or ""
    cache_key = (fam, int(size_px))
    cached = _FONT_OBJ_CACHE.get(cache_key)
    if cached is not None:
        return cached
    if fam:
        path = _resolve_font_path(fam)
        if path:
            try:
                font = cast(ImageFont.ImageFont, ImageFont.truetype(path, size_px))
                _FONT_OBJ_CACHE[cache_key] = font
                return font
            except OSError:
                pass
    for name in ("arialbd.ttf", "arial.ttf"):
        try:
            font = cast(ImageFont.ImageFont, ImageFont.truetype(name, size_px))
            _FONT_OBJ_CACHE[cache_key] = font
            return font
        except OSError:
            pass
    return cast(ImageFont.ImageFont, ImageFont.load_default())


def _fit_font_for_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: float,
    max_h: float,
    prefer_bold: bool,
    font_family: str = "",
    min_size: int = 8,
    max_size: int = 72,
) -> ImageFont.ImageFont:
    if not text:
        return _get_font(min_size)

    max_size = max(min_size, max_size)
    size = min(max_size, max(min_size, int(max_h)))
    while size >= min_size:
        font = _get_font(size, font_family)
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
    font_family: str = "",
    min_size: int = 8,
) -> int:
    size = max(min_size, max_size)
    while size >= min_size:
        font = _get_font(size, font_family)
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
    font_family: str = "",
    min_size: int = 8,
) -> int:
    if scale <= 0:
        return min_size
    factor = ref_scale / scale
    size_ref = _fit_font_size_for_width(
        draw,
        text,
        max_w * factor,
        int(max_size * factor),
        font_family=font_family,
        min_size=min_size,
    )
    return max(min_size, int(size_ref * scale / ref_scale))




def _header_geometry(template: TicketTemplateSpec, grid: GridSpec, scale: float) -> dict[str, float]:
    header_h_mm = max(0.0, float(grid.header_height_mm))
    if header_h_mm <= 0:
        return {}

    pad_px = grid.padding_mm * scale
    x1 = pad_px
    y1 = pad_px
    x2 = (template.width_mm - grid.padding_mm) * scale
    y2 = (grid.padding_mm + header_h_mm) * scale

    stroke_w = max(1, int(grid.line_width_mm * scale))
    # Draw header box with rounded corners
    radius = max(2, int(min(x2 - x1, y2 - y1) * 0.08))

    inner_w = max(1.0, x2 - x1)
    inner_h = max(1.0, y2 - y1)
    gap = max(6.0, inner_w * 0.02)

    # Left: round_name + round_code (nằm gần nhau, không bị ảnh hưởng tên đơn vị)
    left_col_w = inner_w * 0.34
    left_x = x1 + gap

    # Right: org_text / org_image (bên phải, tách riêng)
    right_col_w = inner_w - left_col_w - gap
    right_x = x1 + left_col_w + gap

    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "radius": radius,
        "stroke_w": stroke_w,
        "inner_w": inner_w,
        "inner_h": inner_h,
        "gap": gap,
        "left_col_w": left_col_w,
        "left_x": left_x,
        "right_col_w": right_col_w,
        "right_x": right_x,
    }


def _draw_header_static(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec,
    scale: float,
    ref_scale: float,
) -> None:
    geom = _header_geometry(template, grid, scale)
    if not geom:
        return

    x1 = geom["x1"]
    y1 = geom["y1"]
    x2 = geom["x2"]
    y2 = geom["y2"]
    radius = int(geom["radius"])
    stroke_w = int(geom["stroke_w"])
    inner_h = geom["inner_h"]
    gap = geom["gap"]
    left_col_w = geom["left_col_w"]
    left_x = geom["left_x"]
    right_col_w = geom["right_col_w"]
    right_x = geom["right_x"]

    try:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, outline=(30, 41, 59), width=stroke_w)
    except Exception:
        draw.rectangle([x1, y1, x2, y2], outline=(30, 41, 59), width=stroke_w)

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
            font_family=header.font_family,
            min_size=10,
            max_size=int(available_h * 0.4),
        )
        bbox = draw.textbbox((0, 0), round_text, font=round_font)
        round_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])

    # Only round name in left column for static layer (align to top)
    if round_text and round_font is not None:
        start_y = y1 + gap
        rx = left_x + (left_col_w - round_size[0]) / 2
        draw.text((rx, start_y), round_text, font=round_font, fill=(15, 23, 42))

    # RIGHT COLUMN: Org image or org text
    right_y = y1 + gap
    right_h = inner_h - 2 * gap

    if header.org_image_path:
        try:
            max_img_w = int(right_col_w - 2 * gap)
            max_img_h = int(right_h)
            org_img = _get_cached_org_thumb(header.org_image_path, max_img_w, max_img_h)
            if org_img is not None:
                img_x = int(right_x + (right_col_w - org_img.width) * 0.5)
                img_y = int(right_y + (right_h - org_img.height) * 0.5)
                img.paste(org_img, (img_x, img_y), org_img)
        except Exception:
            pass
    else:
        lines = header.org_text.splitlines() or [""]
        lines = lines[:6]
        max_w = right_col_w - 2 * gap

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
                font_family=header.font_family,
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
            font = _get_font(size, header.font_family)
            bbox = draw.textbbox((0, 0), raw_line, font=font)
            tw = bbox[2] - bbox[0]
            tx = right_x + (right_col_w - tw) / 2
            draw.text((tx, y), raw_line, font=font, fill=(15, 23, 42))
            y += size + gap_h


def _draw_header_round_code(
    draw: ImageDraw.ImageDraw,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec,
    round_code: str | None,
    scale: float,
    ref_scale: float,
) -> None:
    code_text = str(round_code or "").strip().upper()
    if not code_text:
        return
    geom = _header_geometry(template, grid, scale)
    if not geom:
        return

    y1 = geom["y1"]
    inner_h = geom["inner_h"]
    gap = geom["gap"]
    left_col_w = geom["left_col_w"]
    left_x = geom["left_x"]
    radius = int(geom["radius"])
    stroke_w = int(geom["stroke_w"])

    available_h = inner_h - 2 * gap

    round_text = header.round_name
    round_size = (0, 0)
    if round_text:
        round_font = _fit_font_for_text(
            draw,
            round_text,
            max_w=left_col_w - 2 * gap,
            max_h=available_h * 0.35,
            prefer_bold=True,
            font_family=header.font_family,
            min_size=10,
            max_size=int(available_h * 0.4),
        )
        bbox = draw.textbbox((0, 0), round_text, font=round_font)
        round_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])

    code_font = _fit_font_for_text(
        draw,
        code_text,
        max_w=left_col_w - 2 * gap,
        max_h=available_h * 0.55,
        prefer_bold=True,
        font_family=header.font_family,
        min_size=12,
        max_size=int(available_h * 0.6),
    )
    bbox = draw.textbbox((0, 0), code_text, font=code_font)
    seed_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])

    if round_text:
        sy = y1 + gap + round_size[1] + gap * 0.5
    else:
        sy = y1 + (inner_h - seed_size[1]) / 2

    sx = left_x + (left_col_w - seed_size[0]) / 2
    pad = max(4.0, gap * 0.4)
    bbox = draw.textbbox((sx, sy), code_text, font=code_font)
    bx1 = bbox[0] - pad
    by1 = bbox[1] - pad * 0.2
    bx2 = bbox[2] + pad
    by2 = bbox[3] + pad * 1.1
    dash = max(4, int(pad * 0.8))
    gap_len = max(3, int(pad * 0.6))
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
    try:
        draw.arc([bx1, by1, bx1 + 2 * radius, by1 + 2 * radius], 180, 270, fill=(59, 130, 246), width=stroke_w)
        draw.arc([bx2 - 2 * radius, by1, bx2, by1 + 2 * radius], 270, 360, fill=(59, 130, 246), width=stroke_w)
        draw.arc([bx1, by2 - 2 * radius, bx1 + 2 * radius, by2], 90, 180, fill=(59, 130, 246), width=stroke_w)
        draw.arc([bx2 - 2 * radius, by2 - 2 * radius, bx2, by2], 0, 90, fill=(59, 130, 246), width=stroke_w)
    except Exception:
        pass
    draw.text((sx, sy), code_text, font=code_font, fill=(59, 130, 246))


def _draw_footer_seed(
    draw: ImageDraw.ImageDraw,
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec,
    seed: int | None,
    scale: float,
    ref_scale: float,
) -> None:
    if seed is None:
        return

    seed_text = str(seed)
    text = f"Seed: {seed_text}"

    pad_px = max(3.0, grid.padding_mm * scale * 0.55)
    max_w = max(40.0, (template.width_mm * scale) - 2 * pad_px)
    size = _fit_font_size_for_width_scaled(
        draw,
        text,
        max_w=max_w,
        max_size=12,
        scale=scale,
        ref_scale=ref_scale,
        font_family=header.font_family,
        min_size=7,
    )
    font = _get_font(max(6, int(size * 0.75)), header.font_family)
    bbox = draw.textbbox((0, 0), text, font=font)
    th = bbox[3] - bbox[1]

    x = max(1.0, pad_px)
    y = max(1.0, (template.height_mm * scale) - pad_px - th)
    draw.text((x, y), text, font=font, fill=(71, 85, 105))


def _get_header_base(
    template: TicketTemplateSpec,
    grid: GridSpec,
    header: TicketHeaderSpec,
    scale: float,
    ref_scale: float,
) -> Image.Image | None:
    key = (
        float(template.width_mm),
        float(template.height_mm),
        float(grid.header_height_mm),
        float(grid.header_spacing_mm),
        float(grid.padding_mm),
        float(grid.line_width_mm),
        int(grid.row_group_size),
        float(grid.row_group_gap_mm),
        float(scale),
        float(ref_scale),
        str(header.round_name),
        str(header.org_text),
        str(header.org_image_path or ""),
        str(header.font_family),
    )
    cached = _HEADER_BASE_CACHE.get(key)
    if cached is not None:
        return cached
    width_px = max(1, int(template.width_mm * scale))
    height_px = max(1, int(template.height_mm * scale))
    base = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)
    _draw_header_static(base, draw, template, grid, header, scale=scale, ref_scale=ref_scale)
    _HEADER_BASE_CACHE[key] = base
    return base


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
        bg = _get_cached_bg(template.background_path, width_px, height_px)
        if bg is not None:
            img.paste(bg, (0, 0))
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
        base = _get_header_base(template, grid, header, scale=scale, ref_scale=ref_scale)
        if base is not None:
            img.paste(base, (0, 0), base)
        _draw_header_round_code(
            draw,
            template,
            grid,
            header,
            round_code=getattr(header, "round_code", ""),
            scale=scale,
            ref_scale=ref_scale,
        )

    _draw_footer_seed(
        draw,
        template,
        grid,
        header if header is not None else TicketHeaderSpec(),
        seed=seed,
        scale=scale,
        ref_scale=ref_scale,
    )

    rects = _get_cached_rects(template, grid)
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
        font_family = header.font_family if header is not None else ""
        font = _get_font(font_size, font_family)

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


def _page_mm_size(page_size: str, orientation: str) -> tuple[float, float]:
    name = page_size.upper().strip()
    w, h = (210.0, 297.0) if name != "A5" else (148.0, 210.0)
    if orientation.upper() == "LANDSCAPE":
        return h, w
    return w, h


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
    page_w_mm, page_h_mm = _page_mm_size(print_spec.page_size, print_spec.orientation)

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
