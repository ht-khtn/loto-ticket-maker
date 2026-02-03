# RULE – Luật tạo vé (phiên bản 15x6)

## 1) Kích thước & bố cục

- Vé có **15 hàng x 6 cột** (tổng **90 ô**).
- **15 hàng không hiển thị liên tục** mà chia thành **5 nhóm**, mỗi nhóm **3 hàng** (có thể kẻ đường/ngắt khoảng giữa các nhóm khi render/in ấn).

## 2) Miền giá trị

- Tất cả các số từ **1 đến 60** phải xuất hiện **đầy đủ, đúng 1 lần** trên vé.
- Các ô còn lại là ô trống.

## 3) Ràng buộc ô trống theo cột

6 cột (từ trái qua phải) có số lượng ô trống lần lượt là:

- Cột 1: **6** ô trống
- Cột 2: **5** ô trống
- Cột 3: **5** ô trống
- Cột 4: **5** ô trống
- Cột 5: **5** ô trống
- Cột 6: **4** ô trống

Tổng số ô trống theo cột: `6 + 5 + 5 + 5 + 5 + 4 = 30`.

## 4) Ràng buộc ô trống theo hàng

- **Mỗi hàng có đúng 2 ô trống**.
- Vì có 15 hàng nên tổng ô trống theo hàng: `15 * 2 = 30`.

> Hai ràng buộc (theo cột và theo hàng) khớp nhau, đảm bảo luôn có nghiệm hợp lệ.

## 5) Số lượng ô có số

- Tổng ô: `15 * 6 = 90`
- Tổng ô trống: `30`
- Tổng ô có số: `90 - 30 = 60`

Vì vậy có thể đặt đủ các số **1..60** (mỗi số 1 lần).

## 6) Random ("số nhảy random")

"Số nhảy random" được hiểu là:

- **Vị trí ô trống** được tạo ngẫu nhiên nhưng **phải** thỏa tất cả ràng buộc ở mục (3) và (4).
- Sau khi có mask ô trống, các số **1..60** được **xáo trộn ngẫu nhiên** rồi gán vào các ô còn lại.

## 7) Gợi ý thuật toán tạo vé (để implement)

1. Khởi tạo bảng 15x6 với tất cả ô là “chưa quyết định”.
2. Tạo **mask ô trống** thỏa:
   - mỗi hàng đúng 2 ô trống;
   - tổng ô trống từng cột đúng `[6, 5, 5, 5, 5, 4]`.

   Có thể dùng một trong các cách:
   - **Backtracking** theo từng hàng (chọn 2 cột để trống mỗi hàng, giảm dần quota của cột).
   - **Random + retry** có kiểm tra quota cột (kết hợp heuristics: ưu tiên cột còn quota trống lớn).

3. Tạo danh sách `nums = [1..60]`, shuffle bằng RNG/seed.
4. Duyệt các ô theo thứ tự (ví dụ theo hàng), ô không trống thì lấy lần lượt số từ `nums` để điền.
5. Khi render, chèn “đường ngắt nhóm” sau mỗi 3 hàng (hàng 3, 6, 9, 12).
