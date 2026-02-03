"""Các model cấu hình.

Ghi chú:
- Dùng đơn vị mm cho cấu hình in ấn (dễ đúng với thực tế)
- Khi xuất PDF sẽ đổi mm -> points (pt)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TicketTemplateSpec:
    width_mm: float = 100.0
    height_mm: float = 150.0
    background_path: Optional[str] = None  # đường dẫn ảnh nền (tuỳ chọn)


@dataclass(frozen=True)
class GridSpec:
    rows: int = 3
    cols: int = 9
    padding_mm: float = 4.0
    line_width_mm: float = 0.4


@dataclass(frozen=True)
class PrintSpec:
    page_size: str = "A4"  # A4, A5, CUSTOM
    margin_mm: float = 8.0
    spacing_mm: float = 4.0
