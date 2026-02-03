# Loto Ticket Maker (Python GUI)

App tạo vé loto (bingo) với giao diện GUI: tạo nền vé, sinh ô số theo quy luật, render vé hoàn chỉnh, và xuất PDF để in (nhiều vé trên 1 trang, tuỳ chỉnh kích thước).

## Mục tiêu
- Dễ dùng (GUI đẹp, thao tác nhanh)
- Code module hoá, dễ mở rộng/bảo trì
- Xuất PDF in ấn chuẩn, tuỳ chọn layout (A4/A5/custom, lề, số vé/trang)
- Đóng gói thành phần mềm Windows (exe)

## Công nghệ đề xuất
- GUI: **PySide6 (Qt)** — giao diện hiện đại, dễ bố trí layout, preview tốt.
- Xuất PDF: **reportlab** — kiểm soát bố cục in ấn và đặt nhiều vé/trang.
- Render preview (tuỳ chọn): **Pillow** — render ảnh preview nhanh trong GUI.

## Cấu trúc thư mục
- `src/loto_ticket_maker/` mã nguồn chính
  - `main.py` entrypoint
  - `ui/` màn hình, widget
  - `core/` logic sinh ô số, model cấu hình
  - `render/` render vé (preview)
  - `export/` xuất PDF
  - `config/` cấu hình mặc định
- `assets/` template nền, font (nếu có)
- `PLAN.md` kế hoạch triển khai chi tiết

## Yêu cầu môi trường
- Windows 10/11
- Python 3.11+ (khuyến nghị 3.11 hoặc 3.12)

## Cài đặt
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip

# Cài app dạng editable để chạy dev (project dùng layout src/)
pip install -e .

# (Tuỳ chọn) nếu bạn chỉ muốn cài dependency theo file requirements
# pip install -r requirements.txt
```

## Chạy app
```powershell
python -m loto_ticket_maker
```

## Đóng gói thành exe (PyInstaller)
Sau khi ổn định tính năng:
```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --name LotoTicketMaker -m loto_ticket_maker
```
Gợi ý: khi app có asset (ảnh nền, font), cần cấu hình `--add-data`.

## Trạng thái hiện tại
- Đã có khung GUI cơ bản (MainWindow)
- Các module chức năng đang ở dạng skeleton theo kế hoạch

## Góp ý / mở rộng
Bạn có thể xác nhận giúp mình 3 điểm để chốt chuẩn in ấn:
1) Kích thước vé: A6? 10x15cm? hay custom theo mm?
2) Quy luật ô số: dạng 3x9 (loto VN) hay 5x5 (bingo)?
3) Font, màu sắc, logo/QR có cần không?
