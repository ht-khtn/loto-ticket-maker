"""Sinh vị trí các ô theo quy luật.

Trong milestone đầu:
- chỉ cần tạo danh sách các hình chữ nhật (rect) theo rows/cols + padding

Sau đó mở rộng:
- rule loto VN (3x9) / bingo (5x5)
- sinh số theo seed để tái tạo
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import GridSpec, TicketTemplateSpec


@dataclass(frozen=True)
class RectMM:
    x: float
    y: float
    w: float
    h: float


def generate_grid_rects_mm(template: TicketTemplateSpec, grid: GridSpec) -> list[RectMM]:
    """Tạo danh sách rect theo mm trong vùng vé.

    Quy ước: (0,0) là góc trên-trái của vé.
    """
    content_x = grid.padding_mm
    content_y = grid.padding_mm
    content_w = template.width_mm - 2 * grid.padding_mm
    content_h = template.height_mm - 2 * grid.padding_mm

    cell_w = content_w / grid.cols
    cell_h = content_h / grid.rows

    rects: list[RectMM] = []
    for r in range(grid.rows):
        for c in range(grid.cols):
            rects.append(
                RectMM(
                    x=content_x + c * cell_w,
                    y=content_y + r * cell_h,
                    w=cell_w,
                    h=cell_h,
                )
            )
    return rects
