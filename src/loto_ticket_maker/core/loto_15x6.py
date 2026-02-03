"""Luật sinh vé theo RULE.md (15 hàng x 6 cột).

Ràng buộc:
- Grid 15x6.
- Các số 1..60 xuất hiện đầy đủ, mỗi số đúng 1 lần.
- Mỗi hàng có đúng 2 ô trống (tức 4 ô có số).
- Số ô trống theo từng cột (trái -> phải): 6-5-5-5-5-4.
- Random vị trí ô trống và shuffle số; hỗ trợ seed.

Trả về matrix 15x6, mỗi ô là int hoặc None (ô trống).
"""

from __future__ import annotations

import random
from typing import Optional

GridNumbers = list[list[Optional[int]]]


_COL_BLANKS: tuple[int, ...] = (6, 5, 5, 5, 5, 4)
_ROWS = 15
_COLS = 6
_BLANKS_PER_ROW = 2


def _is_feasible(blank_remaining: list[int], rows_left: int) -> bool:
    # Mỗi hàng tiếp theo có thể đóng góp tối đa 1 blank cho mỗi cột.
    # => với rows_left hàng, mỗi cột có thể thêm tối đa rows_left blanks.
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

    # Lấy một subset top để random trong nhóm tốt, tránh bias quá mạnh.
    top_k = min(len(candidates), 12)
    return rng.choice(candidates[:top_k])


def generate_loto_15x6(seed: Optional[int] = None, max_tries: int = 2000) -> GridNumbers:
    """Sinh vé 15x6 theo RULE.md.

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

        nums = list(range(1, 61))
        rng.shuffle(nums)
        it = iter(nums)

        grid: GridNumbers = [[None for _ in range(_COLS)] for _ in range(_ROWS)]
        for r in range(_ROWS):
            c_blank1, c_blank2 = blanks_by_row[r]
            for c in range(_COLS):
                if c == c_blank1 or c == c_blank2:
                    grid[r][c] = None
                else:
                    grid[r][c] = next(it)

        return grid

    raise RuntimeError("Không sinh được vé 15x6 (hết số lần thử).")
