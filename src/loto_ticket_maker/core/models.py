"""Các model cấu hình.

Ghi chú:
- Dùng đơn vị mm cho cấu hình in ấn (dễ đúng với thực tế)
- Khi xuất PDF sẽ đổi mm -> points (pt)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TicketTemplateSpec:
    width_mm: float = 60.0
    height_mm: float = 150.0
    background_path: str | None = None  # đường dẫn ảnh nền (tuỳ chọn)


@dataclass(frozen=True)
class TicketHeaderSpec:
    org_text: str = ""  # nhiều dòng, mỗi dòng auto-fit
    org_image_path: str | None = None
    round_name: str = ""


@dataclass(frozen=True)
class GridSpec:
    rows: int = 15
    cols: int = 6
    padding_mm: float = 4.0
    line_width_mm: float = 0.4

    # Header nằm trên grid (đóng khung, cùng bề rộng với grid)
    header_height_mm: float = 18.0

    # Nhóm hàng (RULE.md: nhóm 3 hàng) và khoảng cách giữa các nhóm
    row_group_size: int = 3
    row_group_gap_mm: float = 2.0

    # Tỉ lệ cỡ chữ số trong ô (so với chiều cao ô)
    number_font_scale: float = 0.55


@dataclass(frozen=True)
class PrintSpec:
    # Export mode:
    # - "TICKET": PDF theo kích thước vé (mỗi vé = 1 trang)
    # - "PAGE": PDF theo trang A4/A5, vé auto-fit theo trang
    mode: str = "PAGE"

    page_size: str = "A4"  # A4, A5
    margin_mm: float = 8.0
    spacing_mm: float = 4.0
    tickets_per_page: int = 6
