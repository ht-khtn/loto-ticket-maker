"""Luật sinh vé theo RULE.md (15 hàng x 6 cột, dải cột cố định).

Ràng buộc:
- Grid 15x6.
- Mỗi cột có dải giá trị cố định:
  - Cột 1: 1–9 (9 số)
  - Cột 2: 10–19 (10 số)
  - Cột 3: 20–29 (10 số)
  - Cột 4: 30–39 (10 số)
  - Cột 5: 40–49 (10 số)
  - Cột 6: 50–60 (11 số)
- Mỗi hàng có đúng 2 ô trống (tức 4 ô có số).
- Số ô trống theo cột: 6-5-5-5-5-4 (cột 1 có 6 trống, cột 6 có 4 trống).
- Random vị trí ô trống và shuffle số trong mỗi cột; hỗ trợ seed.

Trả về matrix 15x6, mỗi ô là int hoặc None (ô trống).
"""

from __future__ import annotations

import random
from typing import Optional

GridNumbers = list[list[Optional[int]]]


_COL_RANGES = [
    range(1, 10),       # Cột 0: 1–9
    range(10, 20),      # Cột 1: 10–19
    range(20, 30),      # Cột 2: 20–29
    range(30, 40),      # Cột 3: 30–39
    range(40, 50),      # Cột 4: 40–49
    range(50, 61),      # Cột 5: 50–60
]

_COL_BLANKS: tuple[int, ...] = (6, 5, 5, 5, 5, 4)
_ROWS = 15
_COLS = 6
_BLANKS_PER_ROW = 2


def _is_feasible(blank_remaining: list[int], rows_left: int) -> bool:
    """Kiểm tra xem có thể điền ô trống vào rows_left hàng tiếp theo hay không."""
    for b in blank_remaining:
        if b < 0 or b > rows_left:
            return False
    return sum(blank_remaining) == rows_left * _BLANKS_PER_ROW


def _pick_row_blanks(
    rng: random.Random,
    blank_remaining: list[int],
    row_index: int,
) -> tuple[int, int] | None:
    """Chọn 2 cột để trống cho 1 hàng.

    Trả về (c1, c2) hoặc None nếu không có lựa chọn hợp lệ.
    """
    rows_left_after = _ROWS - (row_index + 1)

    candidates: list[tuple[int, int]] = []
    for c1 in range(_COLS):
        if blank_remaining[c1] <= 0:
            continue
        for c2 in range(c1 + 1, _COLS):
            if blank_remaining[c2] <= 0:
                continue

            test = blank_remaining.copy()
            test[c1] -= 1
            test[c2] -= 1
            if _is_feasible(test, rows_left_after):
                candidates.append((c1, c2))

    if not candidates:
        return None

    # Heuristic: ưu tiên cột còn nhiều quota trống hơn.
    def score(pair: tuple[int, int]) -> int:
        c1, c2 = pair
        return blank_remaining[c1] + blank_remaining[c2]

    candidates.sort(key=score, reverse=True)
    top_k = min(len(candidates), 12)
    return rng.choice(candidates[:top_k])


def generate_loto_15x6(seed: Optional[int] = None, max_tries: int = 2000) -> GridNumbers:
    """Sinh vé 15x6 theo RULE.md (dải cột cố định).

    `seed`: để tái tạo vé. None -> random.
    """
    rng = random.Random(seed)

    for _ in range(max_tries):
        blank_remaining = list(_COL_BLANKS)
        blanks_by_row: list[tuple[int, int]] = []

        ok = True
        for r in range(_ROWS):
            pair = _pick_row_blanks(rng, blank_remaining, r)
            if pair is None:
                ok = False
                break
            c1, c2 = pair
            blank_remaining[c1] -= 1
            blank_remaining[c2] -= 1
            blanks_by_row.append((c1, c2))

        if not ok:
            continue
        if any(b != 0 for b in blank_remaining):
            continue

        # Sinh grid, mỗi cột có dải riêng
        grid: GridNumbers = [[None for _ in range(_COLS)] for _ in range(_ROWS)]

        for c in range(_COLS):
            # Lấy dải giá trị cho cột c
            col_range = _COL_RANGES[c]
            nums = list(col_range)
            rng.shuffle(nums)
            it = iter(nums)

            # Gán số vào các ô không trống của cột c
            for r in range(_ROWS):
                c_blank1, c_blank2 = blanks_by_row[r]
                if c != c_blank1 and c != c_blank2:
                    grid[r][c] = next(it)

        return grid

    raise RuntimeError("Không sinh được vé 15x6 (hết số lần thử).")
