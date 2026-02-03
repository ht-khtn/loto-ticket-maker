"""Sinh vị trí các ô theo quy luật.

- Tạo danh sách rect theo rows/cols + padding.
- Hỗ trợ header phía trên grid.
- Hỗ trợ gap giữa các nhóm hàng (ví dụ 15 hàng chia nhóm 3 hàng).
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

    Grid rects chỉ bao gồm vùng ô số (không bao gồm header).
    """
    header_h = max(0.0, grid.header_height_mm)
    header_gap = max(0.0, grid.header_spacing_mm)

    content_x = grid.padding_mm
    content_y = grid.padding_mm + header_h + header_gap
    content_w = template.width_mm - 2 * grid.padding_mm
    content_h = template.height_mm - 2 * grid.padding_mm - header_h - header_gap

    if grid.rows <= 0 or grid.cols <= 0:
        return []

    group_size = max(1, int(grid.row_group_size))
    group_gap = max(0.0, float(grid.row_group_gap_mm))
    group_count = (grid.rows + group_size - 1) // group_size
    total_gap = group_gap * max(0, group_count - 1)

    # Trừ khoảng gap để vẫn giữ tổng chiều cao nằm trong content_h
    cell_w = content_w / grid.cols
    cell_h = (content_h - total_gap) / grid.rows

    rects: list[RectMM] = []
    for r in range(grid.rows):
        gap_before = (r // group_size) * group_gap
        y = content_y + r * cell_h + gap_before
        for c in range(grid.cols):
            rects.append(
                RectMM(
                    x=content_x + c * cell_w,
                    y=y,
                    w=cell_w,
                    h=cell_h,
                )
            )
    return rects
