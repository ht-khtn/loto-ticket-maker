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

from ..core.models import GridSpec, PrintSpec, TicketHeaderSpec, TicketTemplateSpec


class TicketTemplateSpecDict(TypedDict):
    width_mm: float
    height_mm: float
    background_path: str | None


class TicketHeaderSpecDict(TypedDict):
    org_text: str
    org_image_path: str | None
    round_name: str
    seed_pad_length: int
    font_family: str


class GridSpecDict(TypedDict):
    rows: int
    cols: int
    padding_mm: float
    line_width_mm: float

    header_height_mm: float
    header_spacing_mm: float
    row_group_size: int
    row_group_gap_mm: float


class PrintSpecDict(TypedDict):
    mode: str
    page_size: str
    orientation: str
    margin_mm: float
    spacing_mm: float
    tickets_per_page: int
    export_quality: str


class PresetDict(TypedDict):
    version: int
    template: TicketTemplateSpecDict
    header: TicketHeaderSpecDict
    grid: GridSpecDict
    print_spec: PrintSpecDict
    ui: "UiStateDict"


class UiStateDict(TypedDict):
    seed: int
    ticket_count: int


_PRESET_VERSION = 3


def save_preset(
    path: str,
    template: TicketTemplateSpec,
    header: TicketHeaderSpec,
    grid: GridSpec,
    print_spec: PrintSpec,
    seed: int,
    ticket_count: int,
) -> None:
    data: PresetDict = {
        "version": _PRESET_VERSION,
        "template": {
            "width_mm": float(template.width_mm),
            "height_mm": float(template.height_mm),
            "background_path": template.background_path,
        },
        "header": {
            "org_text": str(header.org_text),
            "org_image_path": header.org_image_path,
            "round_name": str(header.round_name),
            "seed_pad_length": int(header.seed_pad_length),
            "font_family": str(header.font_family),
        },
        "grid": {
            "rows": int(grid.rows),
            "cols": int(grid.cols),
            "padding_mm": float(grid.padding_mm),
            "line_width_mm": float(grid.line_width_mm),

            "header_height_mm": float(grid.header_height_mm),
            "header_spacing_mm": float(grid.header_spacing_mm),
            "row_group_size": int(grid.row_group_size),
            "row_group_gap_mm": float(grid.row_group_gap_mm),
        },
        "print_spec": {
            "mode": str(print_spec.mode),
            "page_size": str(print_spec.page_size),
            "orientation": str(print_spec.orientation),
            "margin_mm": float(print_spec.margin_mm),
            "spacing_mm": float(print_spec.spacing_mm),
            "tickets_per_page": int(print_spec.tickets_per_page),
            "export_quality": str(print_spec.export_quality),
        },
        "ui": {
            "seed": int(seed),
            "ticket_count": int(ticket_count),
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_preset(path: str) -> tuple[TicketTemplateSpec, TicketHeaderSpec, GridSpec, PrintSpec, UiStateDict]:
    with open(path, "r", encoding="utf-8") as f:
        raw: Any = json.load(f)

    if not isinstance(raw, dict):
        raise ValueError("Preset không hợp lệ (không phải object JSON).")

    raw_obj = cast(dict[str, object], raw)

    version = raw_obj.get("version")
    if not isinstance(version, int) or version not in (1, 2, 3):
        raise ValueError(f"Preset version không hỗ trợ: {version}")

    t_any = raw_obj.get("template")
    h_any = raw_obj.get("header") if version >= 2 else None
    g_any = raw_obj.get("grid")
    p_any = raw_obj.get("print_spec")
    ui_any = raw_obj.get("ui")
    if not isinstance(t_any, dict) or not isinstance(g_any, dict) or not isinstance(p_any, dict):
        raise ValueError("Preset thiếu template/grid/print_spec.")

    t_obj = cast(dict[str, object], t_any)
    h_obj = cast(dict[str, object], h_any) if isinstance(h_any, dict) else {}
    g_obj = cast(dict[str, object], g_any)
    p_obj = cast(dict[str, object], p_any)
    ui_obj = cast(dict[str, object], ui_any) if isinstance(ui_any, dict) else {}

    width = t_obj.get("width_mm")
    height = t_obj.get("height_mm")
    bg = t_obj.get("background_path")
    if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
        raise ValueError("TemplateSpec không hợp lệ (width_mm/height_mm).")
    background_path = None
    if isinstance(bg, str) and bg.strip():
        background_path = bg

    org_text = h_obj.get("org_text")
    org_image_path = h_obj.get("org_image_path")
    round_name = h_obj.get("round_name")
    seed_pad_length = h_obj.get("seed_pad_length")
    font_family = h_obj.get("font_family")

    header = TicketHeaderSpec(
        org_text=str(org_text) if isinstance(org_text, str) else "",
        org_image_path=str(org_image_path) if isinstance(org_image_path, str) and org_image_path.strip() else None,
        round_name=str(round_name) if isinstance(round_name, str) else "",
        seed_pad_length=int(seed_pad_length) if isinstance(seed_pad_length, int) else 0,
        font_family=str(font_family) if isinstance(font_family, str) else "",
    )

    rows = g_obj.get("rows")
    cols = g_obj.get("cols")
    padding = g_obj.get("padding_mm")
    line_w = g_obj.get("line_width_mm")
    if not isinstance(rows, int) or not isinstance(cols, int):
        raise ValueError("GridSpec không hợp lệ (rows/cols).")
    if not isinstance(padding, (int, float)) or not isinstance(line_w, (int, float)):
        raise ValueError("GridSpec không hợp lệ (padding_mm/line_width_mm).")

    header_height_mm = g_obj.get("header_height_mm")
    header_spacing_mm = g_obj.get("header_spacing_mm")
    row_group_size = g_obj.get("row_group_size")
    row_group_gap_mm = g_obj.get("row_group_gap_mm")

    # v1 preset không có các field này -> dùng default
    if not isinstance(header_height_mm, (int, float)):
        header_height_mm = GridSpec().header_height_mm
    if not isinstance(header_spacing_mm, (int, float)):
        header_spacing_mm = GridSpec().header_spacing_mm
    if not isinstance(row_group_size, int):
        row_group_size = GridSpec().row_group_size
    if not isinstance(row_group_gap_mm, (int, float)):
        row_group_gap_mm = GridSpec().row_group_gap_mm

    mode = p_obj.get("mode")
    page_size = p_obj.get("page_size")
    orientation = p_obj.get("orientation")
    margin = p_obj.get("margin_mm")
    spacing = p_obj.get("spacing_mm")
    tickets_per_page = p_obj.get("tickets_per_page")
    export_quality = p_obj.get("export_quality")
    if not isinstance(page_size, str):
        raise ValueError("PrintSpec không hợp lệ (page_size).")
    if not isinstance(orientation, str):
        orientation = PrintSpec().orientation
    if not isinstance(margin, (int, float)) or not isinstance(spacing, (int, float)):
        raise ValueError("PrintSpec không hợp lệ (margin_mm/spacing_mm).")

    if not isinstance(mode, str):
        mode = PrintSpec().mode
    if not isinstance(tickets_per_page, int):
        tickets_per_page = PrintSpec().tickets_per_page
    if not isinstance(export_quality, str):
        export_quality = PrintSpec().export_quality

    template = TicketTemplateSpec(width_mm=float(width), height_mm=float(height), background_path=background_path)
    grid = GridSpec(
        rows=rows,
        cols=cols,
        padding_mm=float(padding),
        line_width_mm=float(line_w),
        header_height_mm=float(header_height_mm),
        header_spacing_mm=float(header_spacing_mm),
        row_group_size=int(row_group_size),
        row_group_gap_mm=float(row_group_gap_mm),
    )
    print_spec = PrintSpec(
        mode=str(mode),
        page_size=page_size,
        orientation=str(orientation),
        margin_mm=float(margin),
        spacing_mm=float(spacing),
        tickets_per_page=int(tickets_per_page),
        export_quality=str(export_quality),
    )

    ui_seed = ui_obj.get("seed")
    ui_ticket_count = ui_obj.get("ticket_count")
    ui_state: UiStateDict = {
        "seed": int(ui_seed) if isinstance(ui_seed, int) else 0,
        "ticket_count": int(ui_ticket_count) if isinstance(ui_ticket_count, int) else 6,
    }

    return template, header, grid, print_spec, ui_state
