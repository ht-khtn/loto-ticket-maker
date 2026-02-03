# RULE – Luật tạo vé (phiên bản 15x6)

## 1) Kích thước & bố cục

- Vé có **15 hàng x 6 cột** (tổng **90 ô**).
- **15 hàng không hiển thị liên tục** mà chia thành **5 nhóm**, mỗi nhóm **3 hàng** (có thể kẻ đường/ngắt khoảng giữa các nhóm khi render/in ấn).

## 2) Dải giá trị theo cột

Mỗi cột chứa một dải giá trị cố định:

- **Cột 1**: 1–9 (tổng 9 số)
- **Cột 2**: 10–19 (tổng 10 số)
- **Cột 3**: 20–29 (tổng 10 số)
- **Cột 4**: 30–39 (tổng 10 số)
- **Cột 5**: 40–49 (tổng 10 số)
- **Cột 6**: 50–60 (tổng 11 số)

Mỗi số từ **1 đến 60** xuất hiện **đúng 1 lần** trên vé, ở cột tương ứng với dải của nó.

## 3) Ràng buộc ô trống theo cột

Số ô trống theo từng cột (từ trái qua phải):

- Cột 1: **6** ô trống → **9 ô có số** (dùng hết dải 1–9)
- Cột 2: **5** ô trống → **10 ô có số** (dùng hết dải 10–19)
- Cột 3: **5** ô trống → **10 ô có số** (dùng hết dải 20–29)
- Cột 4: **5** ô trống → **10 ô có số** (dùng hết dải 30–39)
- Cột 5: **5** ô trống → **10 ô có số** (dùng hết dải 40–49)
- Cột 6: **4** ô trống → **11 ô có số** (dùng hết dải 50–60)

Tổng ô trống: `6 + 5 + 5 + 5 + 5 + 4 = 30`.
Tổng ô có số: `9 + 10 + 10 + 10 + 10 + 11 = 60`.

## 4) Ràng buộc ô trống theo hàng

- **Mỗi hàng có đúng 2 ô trống** (tức 4 ô có số).
- Vì có 15 hàng nên tổng ô trống theo hàng: `15 * 2 = 30`.

## 5) Random ("số nhảy random")

- **Vị trí ô trống** được tạo ngẫu nhiên nhưng **phải** thỏa tất cả ràng buộc ở mục (3) và (4).
- **Vị trí các số**: Sau khi có mask ô trống, các số trong mỗi cột được **xáo trộn ngẫu nhiên** rồi gán vào các ô không trống của cột đó.
- **Hỗ trợ seed**: Để tái tạo vé giống nhau.

## 6) Gợi ý thuật toán tạo vé

1. Khởi tạo bảng 15x6 với tất cả ô là "chưa quyết định".

2. Tạo **mask ô trống** thỏa:
   - mỗi hàng đúng 2 ô trống;
   - tổng ô trống từng cột đúng `[6, 5, 5, 5, 5, 4]`.

   Có thể dùng **backtracking** hoặc **random + retry** như trước.

3. Cho mỗi cột `c`:
   - Lấy dải giá trị tương ứng (ví dụ cột 1 → 1..9)
   - Shuffle danh sách số bằng RNG/seed
   - Gán các số vào các ô không trống của cột (theo hàng)

4. Khi render, chèn "đường ngắt nhóm" sau mỗi 3 hàng (hàng 3, 6, 9, 12).
