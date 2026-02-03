"""Render vé sang ảnh để preview trong GUI.

Milestone đầu có thể:
- tạo ảnh nền trắng
- vẽ grid (line)

Sau đó:
- chèn background image
- vẽ số, font, style
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..core.grid_generator import generate_grid_rects_mm
from ..core.models import GridSpec, TicketTemplateSpec


def _get_font(size_px: int) -> ImageFont.ImageFont:
    # Ưu tiên font phổ biến trên Windows; fallback về default.
    for name in ("arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size_px)
        except OSError:
            pass
    return ImageFont.load_default()


def render_ticket_preview(
    template: TicketTemplateSpec,
    grid: GridSpec,
    numbers: list[list[int | None]] | None = None,
    scale: float = 4.0,
) -> Image.Image:
    """Render vé ra ảnh PIL.

    `scale` = số pixel cho mỗi mm (xấp xỉ). Dùng cho preview, không dùng cho in.
    """
    width_px = max(1, int(template.width_mm * scale))
    height_px = max(1, int(template.height_mm * scale))

    img = Image.new("RGB", (width_px, height_px), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    rects = generate_grid_rects_mm(template, grid)
    for rect in rects:
        x1 = rect.x * scale
        y1 = rect.y * scale
        x2 = (rect.x + rect.w) * scale
        y2 = (rect.y + rect.h) * scale
        draw.rectangle([x1, y1, x2, y2], outline=(30, 41, 59), width=1)

    if numbers is not None:
        # Vẽ số vào giữa ô
        cell_w_px = (template.width_mm - 2 * grid.padding_mm) * scale / grid.cols
        cell_h_px = (template.height_mm - 2 * grid.padding_mm) * scale / grid.rows
        font_size = max(10, int(min(cell_w_px, cell_h_px) * 0.45))
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
