"""Load/Save preset cấu hình (JSON).

Preset chứa 3 phần:
- template: TicketTemplateSpec
- grid: GridSpec
- print_spec: PrintSpec

Mục tiêu: lưu nhanh cấu hình để tái sử dụng.
"""

from __future__ import annotations

import json
from typing import Any, TypedDict, cast

from ..core.models import GridSpec, PrintSpec, TicketTemplateSpec


class TicketTemplateSpecDict(TypedDict):
    width_mm: float
    height_mm: float
    background_path: str | None


class GridSpecDict(TypedDict):
    rows: int
    cols: int
    padding_mm: float
    line_width_mm: float


class PrintSpecDict(TypedDict):
    page_size: str
    margin_mm: float
    spacing_mm: float


class PresetDict(TypedDict):
    version: int
    template: TicketTemplateSpecDict
    grid: GridSpecDict
    print_spec: PrintSpecDict


_PRESET_VERSION = 1


def save_preset(path: str, template: TicketTemplateSpec, grid: GridSpec, print_spec: PrintSpec) -> None:
    data: PresetDict = {
        "version": _PRESET_VERSION,
        "template": {
            "width_mm": float(template.width_mm),
            "height_mm": float(template.height_mm),
            "background_path": template.background_path,
        },
        "grid": {
            "rows": int(grid.rows),
            "cols": int(grid.cols),
            "padding_mm": float(grid.padding_mm),
            "line_width_mm": float(grid.line_width_mm),
        },
        "print_spec": {
            "page_size": str(print_spec.page_size),
            "margin_mm": float(print_spec.margin_mm),
            "spacing_mm": float(print_spec.spacing_mm),
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_preset(path: str) -> tuple[TicketTemplateSpec, GridSpec, PrintSpec]:
    with open(path, "r", encoding="utf-8") as f:
        raw: Any = json.load(f)

    if not isinstance(raw, dict):
        raise ValueError("Preset không hợp lệ (không phải object JSON).")

    raw_obj = cast(dict[str, object], raw)

    version = raw_obj.get("version")
    if not isinstance(version, int) or version != _PRESET_VERSION:
        raise ValueError(f"Preset version không hỗ trợ: {version}")

    t_any = raw_obj.get("template")
    g_any = raw_obj.get("grid")
    p_any = raw_obj.get("print_spec")
    if not isinstance(t_any, dict) or not isinstance(g_any, dict) or not isinstance(p_any, dict):
        raise ValueError("Preset thiếu template/grid/print_spec.")

    t_obj = cast(dict[str, object], t_any)
    g_obj = cast(dict[str, object], g_any)
    p_obj = cast(dict[str, object], p_any)

    width = t_obj.get("width_mm")
    height = t_obj.get("height_mm")
    bg = t_obj.get("background_path")
    if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
        raise ValueError("TemplateSpec không hợp lệ (width_mm/height_mm).")
    background_path = None
    if isinstance(bg, str) and bg.strip():
        background_path = bg

    rows = g_obj.get("rows")
    cols = g_obj.get("cols")
    padding = g_obj.get("padding_mm")
    line_w = g_obj.get("line_width_mm")
    if not isinstance(rows, int) or not isinstance(cols, int):
        raise ValueError("GridSpec không hợp lệ (rows/cols).")
    if not isinstance(padding, (int, float)) or not isinstance(line_w, (int, float)):
        raise ValueError("GridSpec không hợp lệ (padding_mm/line_width_mm).")

    page_size = p_obj.get("page_size")
    margin = p_obj.get("margin_mm")
    spacing = p_obj.get("spacing_mm")
    if not isinstance(page_size, str):
        raise ValueError("PrintSpec không hợp lệ (page_size).")
    if not isinstance(margin, (int, float)) or not isinstance(spacing, (int, float)):
        raise ValueError("PrintSpec không hợp lệ (margin_mm/spacing_mm).")

    template = TicketTemplateSpec(width_mm=float(width), height_mm=float(height), background_path=background_path)
    grid = GridSpec(rows=rows, cols=cols, padding_mm=float(padding), line_width_mm=float(line_w))
    print_spec = PrintSpec(page_size=page_size, margin_mm=float(margin), spacing_mm=float(spacing))

    return template, grid, print_spec
