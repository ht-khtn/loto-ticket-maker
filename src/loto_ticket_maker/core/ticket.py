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


def encode_round_code_to_digits(round_code: str) -> str:
    """Mã vòng -> chuỗi chữ số để ghép vào seed.

    Quy tắc:
    - 0..9: giữ nguyên
    - A..Z (không phân biệt hoa/thường): đổi sang mã ASCII (A=65..Z=90)
    - ký tự khác: bỏ qua
    """

    code = str(round_code or "").strip().upper()
    parts: list[str] = []
    for ch in code:
        if "0" <= ch <= "9":
            parts.append(ch)
        elif "A" <= ch <= "Z":
            parts.append(str(ord(ch)))
    return "".join(parts)


def compose_ticket_seed(round_code: str, base_seed: int | None) -> int | None:
    """Seed vé = (mã vòng đã encode) + (seed gốc).

    Nếu base_seed=None thì trả None.
    Nếu round_code rỗng/không hợp lệ thì seed vé = seed gốc.
    """

    if base_seed is None:
        return None
    seed_value = int(base_seed)
    prefix = encode_round_code_to_digits(round_code)
    if not prefix:
        return seed_value
    return int(f"{prefix}{seed_value}")
