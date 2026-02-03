"""Layout helper để sắp vé lên trang.

Dùng chung cho:
- export PDF (A4/A5)
- preview page (PIL)

Tất cả tham số dùng mm.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageLayout:
    rows: int
    cols: int
    scale: float


def compute_page_layout(
    page_w_mm: float,
    page_h_mm: float,
    ticket_w_mm: float,
    ticket_h_mm: float,
    margin_mm: float,
    spacing_mm: float,
    tickets_per_page: int,
) -> PageLayout:
    """Tìm (rows, cols) và scale để nhét N vé vào trang.

    - Giữ đúng tỉ lệ vé (scale đồng nhất).
    - Chừa margin.
    - Có spacing giữa vé.
    """
    n = max(1, int(tickets_per_page))
    margin = max(0.0, float(margin_mm))
    spacing = max(0.0, float(spacing_mm))

    avail_w = max(1e-6, float(page_w_mm) - 2 * margin)
    avail_h = max(1e-6, float(page_h_mm) - 2 * margin)

    best: PageLayout | None = None

    # Duyệt số hàng, suy ra số cột tối thiểu
    for rows in range(1, n + 1):
        cols = (n + rows - 1) // rows

        need_w = cols * ticket_w_mm + max(0, cols - 1) * spacing
        need_h = rows * ticket_h_mm + max(0, rows - 1) * spacing

        if need_w <= 0 or need_h <= 0:
            continue

        scale = min(avail_w / need_w, avail_h / need_h)
        if scale <= 0:
            continue

        # Ưu tiên scale lớn nhất; nếu bằng nhau, ưu tiên ít cols hơn để dễ đọc.
        if best is None or scale > best.scale + 1e-9 or (abs(scale - best.scale) <= 1e-9 and cols < best.cols):
            best = PageLayout(rows=rows, cols=cols, scale=scale)

    if best is None:
        # fallback, dù scale có thể rất nhỏ
        return PageLayout(rows=1, cols=n, scale=1e-3)

    return best
