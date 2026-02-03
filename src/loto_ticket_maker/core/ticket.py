"""Model vé (dữ liệu để render/export)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import GridSpec, TicketTemplateSpec


GridNumbers = list[list[Optional[int]]]


@dataclass(frozen=True)
class Ticket:
    template: TicketTemplateSpec
    grid: GridSpec
    numbers: GridNumbers
    seed: Optional[int] = None
