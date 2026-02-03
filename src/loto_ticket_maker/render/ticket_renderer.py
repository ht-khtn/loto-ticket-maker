"""Render vé sang ảnh để preview trong GUI.

Milestone đầu có thể:
- tạo ảnh nền trắng
- vẽ grid (line)

Sau đó:
- chèn background image
- vẽ số, font, style
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from ..core.grid_generator import generate_grid_rects_mm
from ..core.models import GridSpec, TicketTemplateSpec


def render_ticket_preview(
    template: TicketTemplateSpec,
    grid: GridSpec,
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

    return img
