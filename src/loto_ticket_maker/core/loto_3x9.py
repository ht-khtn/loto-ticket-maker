"""Luật sinh vé loto 3x9 (kiểu VN / tambola).

Tóm tắt luật chuẩn (1 vé):
- Lưới 3 hàng x 9 cột.
- Tổng 15 số trên 1 vé.
- Mỗi hàng có đúng 5 số (4 ô trống).
- Mỗi cột có ít nhất 1 số.
- Dải giá trị theo cột:
  - Cột 1: 1–9
  - Cột 2: 10–19
  - ...
  - Cột 8: 70–79
  - Cột 9: 80–90
- Trong mỗi cột, số tăng dần từ trên xuống.

Ghi chú:
- Có nhiều biến thể ngoài thực tế. Ở đây chọn biến thể phổ biến: mỗi cột có 1 hoặc 2 số
  (vì 9 cột bắt buộc >=1 số => tổng tối thiểu 9; cần 15 số => thêm 6 số, tức 6 cột có 2 số).
"""

from __future__ import annotations

import random
from typing import Optional


GridNumbers = list[list[Optional[int]]]


def _column_ranges() -> list[range]:
    ranges: list[range] = []
    ranges.append(range(1, 10))
    for start in range(10, 80, 10):
        ranges.append(range(start, start + 10))
    ranges.append(range(80, 91))
    return ranges


def generate_loto_3x9(seed: Optional[int] = None, max_tries: int = 500) -> GridNumbers:
    """Sinh ma trận số 3x9 theo luật.

    Trả về matrix 3x9, mỗi ô là `int` hoặc `None` (ô trống).

    `seed`: để tái tạo vé. Nếu None -> random.
    """

    rng = random.Random(seed)

    col_ranges = _column_ranges()

    # Phân phối số theo cột: 9 cột đều có >=1 số, tổng 15 số -> thêm 6 cột có 2 số
    base_counts = [1] * 9
    for idx in rng.sample(range(9), 6):
        base_counts[idx] += 1  # thành 2

    # Lấy số cho từng cột
    col_numbers: list[list[int]] = []
    for col_idx, count in enumerate(base_counts):
        nums = rng.sample(list(col_ranges[col_idx]), count)
        nums.sort()
        col_numbers.append(nums)

    # Gán vị trí vào 3 hàng sao cho mỗi hàng đúng 5 số
    for _ in range(max_tries):
        row_counts = [0, 0, 0]
        placements: list[list[int]] = [[] for _ in range(9)]  # mỗi cột -> danh sách row index

        columns_order = list(range(9))
        rng.shuffle(columns_order)

        ok = True
        for col_idx in columns_order:
            need = base_counts[col_idx]

            available_rows = [r for r in range(3) if row_counts[r] < 5]
            if len(available_rows) < need:
                ok = False
                break

            # Ưu tiên hàng ít số hơn
            available_rows.sort(key=lambda r: row_counts[r])

            if need == 1:
                chosen = [available_rows[0]]
            else:
                # chọn 2 hàng khác nhau
                # ưu tiên 2 hàng ít số nhất; nếu trùng logic vẫn ổn vì list unique
                chosen = available_rows[:2]

            for r in chosen:
                row_counts[r] += 1
            placements[col_idx] = sorted(chosen)

        if not ok:
            continue

        if row_counts != [5, 5, 5]:
            continue

        grid: GridNumbers = [[None for _ in range(9)] for _ in range(3)]

        # Fill: đảm bảo tăng dần theo cột từ trên xuống
        for col_idx in range(9):
            rows_for_col = placements[col_idx]
            nums = col_numbers[col_idx]
            if len(rows_for_col) != len(nums):
                ok = False
                break

            # rows_for_col đã sorted, nums đã sorted
            for r, n in zip(rows_for_col, nums, strict=True):
                grid[r][col_idx] = n

        if ok:
            return grid

    raise RuntimeError("Không sinh được vé loto 3x9 (hết số lần thử).")
