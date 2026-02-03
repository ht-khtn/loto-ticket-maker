from __future__ import annotations

from loto_ticket_maker.core.models import GridSpec, PrintSpec, TicketHeaderSpec, TicketTemplateSpec


DEFAULT_TEMPLATE = TicketTemplateSpec(
    width_mm=60.0,
    height_mm=150.0,
)

DEFAULT_HEADER = TicketHeaderSpec(
    org_text="",
    org_image_path=None,
    round_name="",
)

DEFAULT_GRID = GridSpec(
    rows=15,
    cols=6,
    header_height_mm=18.0,
    row_group_size=3,
    row_group_gap_mm=2.0,
    number_font_scale=0.55,
)

DEFAULT_PRINT = PrintSpec(
    mode="PAGE",
    page_size="A4",
    margin_mm=5.0,
    spacing_mm=2.0,
    tickets_per_page=6,
)
