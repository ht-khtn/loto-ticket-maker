"""Defaults cho app."""

from __future__ import annotations

from ..core.models import GridSpec, PrintSpec, TicketTemplateSpec

DEFAULT_TEMPLATE = TicketTemplateSpec(width_mm=100.0, height_mm=150.0)
DEFAULT_GRID = GridSpec(rows=15, cols=6, padding_mm=4.0, line_width_mm=0.4)
DEFAULT_PRINT = PrintSpec(page_size="A4", margin_mm=8.0, spacing_mm=4.0)
