# Kế hoạch triển khai — Loto Ticket Maker

Ngày: 2026-02-03

## 1) Phạm vi & đầu ra

**App GUI** cho phép:

- Tạo nền vé (background/template) không có ô
- Sinh hệ thống ô số theo quy luật (kích thước, số hàng/cột, margin, bo góc, style)
- Vẽ ô lên nền -> vé hoàn chỉnh (preview)
- Xuất PDF in ấn: tuỳ chỉnh khổ giấy, lề, khoảng cách, in nhiều vé trên 1 trang
- Có thể đóng gói thành phần mềm Windows

## 2) Quyết định kỹ thuật

### GUI

- PyQt5 (Qt5): tương thích 32-bit, layout đẹp, dễ mở rộng (toolbox, sidebar, live preview)

### Render & PDF

- Preview: render sang ảnh (PIL Image) rồi hiển thị trong Qt
- PDF: dùng reportlab để:
  - đặt nhiều vé/trang theo grid
  - canh lề theo mm
  - chọn page size A4/A5/custom
  - xuất vector/bitmap tuỳ nhu cầu

### Đóng gói

- PyInstaller tạo `.exe`
- Quản lý assets (ảnh nền, font) theo thư mục `assets/`

## 3) Thiết kế module

### Core (logic)

- `core/models.py`
  - `TicketTemplateSpec`: kích thước vé (mm), nền (file), vùng nội dung
  - `GridSpec`: rows/cols, padding, line width, style
  - `PrintSpec`: khổ giấy, margin, số vé/trang, spacing
- `core/grid_generator.py`
  - Sinh danh sách ô (rect) theo spec
  - (tuỳ chọn) Sinh số theo rule (3x9 loto VN, 5x5 bingo, random/seed)

### Render

- `render/ticket_renderer.py`
  - Nhận template + grid + numbers -> render preview (PIL Image)
  - Tách riêng màu, font, độ dày line

### Export

- `export/pdf_exporter.py`
  - Xuất PDF: 1 vé / nhiều vé / nhiều trang
  - Layout engine: tính vị trí từng vé trên trang

### UI

- `ui/main_window.py`
  - Sidebar: chọn template, chỉnh grid, chỉnh in ấn
  - Preview: hiển thị vé, zoom, pan
  - Buttons: Generate / Export PDF / Save Preset

## 4) Các mốc triển khai (milestones)

### M1 — Khung app + cấu hình

- Chạy được GUI
- Load/save cấu hình (JSON) cho template/grid/print

### M2 — Sinh ô theo quy luật

- Implement grid generator
- Preview vẽ ô lên nền (chưa cần số)

### M3 — Số & rule

- Thêm rule sinh số (bạn chốt: theo RULE.md — 15x6, đủ 1..60)
- Seed để tái tạo vé

### M4 — Xuất PDF in nhiều vé/trang

- A4/A5/custom
- Tuỳ chỉnh margins, spacing, scale
- Xuất nhiều vé, đánh số vé

### M5 — Hoàn thiện UX + đóng gói

- Style UI (QSS), icon, preset
- PyInstaller build
- Bộ test cơ bản cho grid/layout

## 5) Rủi ro & cách giảm

- Sai lệch kích thước in: chuẩn hoá đơn vị mm->pt (reportlab) và test in 100%
- Asset paths khi đóng gói: dùng đường dẫn tương đối + PyInstaller hooks

## 6) Việc cần bạn xác nhận

Đã chốt:

- Dạng vé: **15x6 theo RULE.md**
- Khổ giấy in: **A4**

Còn cần bạn xác nhận thêm:

1. Kích thước vé (mm) theo mẫu bạn muốn in.
2. Có cần logo/QR/serial, hoặc vùng ghi thông tin không?
