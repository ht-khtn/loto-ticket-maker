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

- [x] Implement rule mới theo RULE.md (15x6, dải cột cố định 1-9/10-19/.../50-60)
- [x] Seed để tái tạo vé

### M4 — Xuất PDF in nhiều vé/trang

- [x] Xuất PDF A4 nhiều vé/trang (per_row x per_col)
- [x] Kiểm tra layout: báo lỗi nếu không đủ chỗ
- [x] Thêm mode xuất "vé thường" (PDF theo kích thước vé, mỗi vé 1 trang)
- [x] Thêm mode xuất theo trang A4/A5 (auto-fit theo tickets_per_page)
- [x] Preview khớp mode xuất (preview vé vs preview trang)

### M5 — Hoàn thiện UX + đóng gói (tuỳ chọn)

- [x] Style UI (QSS)
- [x] Popups/dialogs dễ đọc (QMessageBox/QFileDialog)
- [x] Các nhóm tuỳ chọn dạng collapsible (mặc định thu gọn)
- [x] Header block: đơn vị/logo, tên vòng, seed lớn
- [x] Điều khiển cỡ chữ số + gap nhóm 3 hàng
- [x] Preset container riêng + có preset mẫu
- [x] Việt hoá nhãn UI (dọc/ngang, nhãn gọn gàng)
- [ ] PyInstaller build (exe)
- [ ] Bộ test cơ bản cho grid/layout

## RULE.md (Bắt buộc)

- [x] Grid 15 hàng x 6 cột
- [x] Chia 15 hàng thành 5 nhóm (mỗi nhóm 3 hàng) khi render/in
- [x] Dải cột cố định: cột 1→1-9, cột 2→10-19, ..., cột 6→50-60
- [x] Mỗi số 1-60 xuất hiện đúng 1 lần (ở cột phù hợp)
- [x] Ô trống theo cột: 6-5-5-5-5-4
- [x] Mỗi hàng có đúng 2 ô trống
- [x] Random hoá vị trí trống + shuffle số trong cột (hỗ trợ seed)

## Diagnostics

- [x] Workspace không còn lỗi (strict)
