# PROCESS CHECK — Theo dõi triển khai

File này dùng để tick các hạng mục đã làm được theo [PLAN.md](PLAN.md) và [RULE.md](RULE.md).

## PLAN.md (Milestones)

### M1 — Khung app + cấu hình

- [x] GUI chạy được (MainWindow)
- [x] Load/Save cấu hình (JSON) cho template/grid/print

### M2 — Sinh ô theo quy luật

- [x] Grid generator tạo rect theo rows/cols + padding
- [x] Preview vẽ ô lên nền (PIL -> Qt)

### M3 — Số & rule

- [x] Implement rule mới theo RULE.md (15x6, đủ 1..60, ràng buộc ô trống)
- [x] Seed để tái tạo vé

### M4 — Xuất PDF in nhiều vé/trang

- [x] Xuất PDF A4 nhiều vé/trang (per_row x per_col)
- [x] Kiểm tra layout: báo lỗi nếu không đủ chỗ

### M5 — Hoàn thiện UX + đóng gói (tuỳ chọn)

- [x] Style UI (QSS)
- [ ] PyInstaller build (exe)
- [ ] Bộ test cơ bản cho grid/layout

## RULE.md (Bắt buộc)

- [x] Grid 15 hàng x 6 cột
- [x] Chia 15 hàng thành 5 nhóm (mỗi nhóm 3 hàng) khi render/in
- [x] Đủ số 1..60, mỗi số đúng 1 lần
- [x] Ô trống theo cột: 6-5-5-5-5-4
- [x] Mỗi hàng có đúng 2 ô trống
- [x] Random hoá vị trí trống + shuffle số (hỗ trợ seed)

## Diagnostics

- [x] Workspace không còn lỗi (strict)
