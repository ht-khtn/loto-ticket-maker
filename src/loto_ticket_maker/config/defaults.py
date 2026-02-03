from __future__ import annotations

from loto_ticket_maker.core.models import GridSpec, PrintSpec, TicketHeaderSpec, TicketTemplateSpec


DEFAULT_TEMPLATE = TicketTemplateSpec(
    width_mm=100.0,
    height_mm=300.0,
)

DEFAULT_HEADER = TicketHeaderSpec(
    org_text="",
    org_image_path=None,
    round_name="",
    seed_pad_length=0,
)

DEFAULT_GRID = GridSpec(
    rows=15,
    cols=6,
    header_height_mm=25.0,
    header_spacing_mm=5.0,
    row_group_size=3,
    row_group_gap_mm=2.0,
)

DEFAULT_PRINT = PrintSpec(
    mode="TICKET",
    page_size="A4",
    margin_mm=5.0,
    spacing_mm=2.0,
    tickets_per_page=6,
)
