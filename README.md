# Hệ thống tư vấn dinh dưỡng và gợi ý thực đơn

## 1. Giới thiệu

Repository của **Nhóm 1**, môn **Các hệ cơ sở tri thức – CS217.R11**, phục vụ **Bài thực hành 2 (BTTH2)** với đề tài **Hệ thống tư vấn dinh dưỡng và gợi ý thực đơn**.

Theo phạm vi BTTH1, hệ thống hướng đến hỗ trợ lựa chọn thực phẩm và xây dựng thực đơn dựa trên thông tin cá nhân (độ tuổi, nhu cầu dinh dưỡng, mức độ hoạt động thể chất), thực phẩm và nhóm thực phẩm, thành phần và hàm lượng dinh dưỡng, dị ứng, chế độ ăn, sở thích, mục tiêu dinh dưỡng, món ăn và bữa ăn. Các chức năng dự kiến gồm tra cứu tri thức, kiểm tra thực phẩm phù hợp, phát hiện xung đột với dị ứng/chế độ ăn, đề xuất thực phẩm và thực đơn, giải thích kết quả tư vấn.

BTTH2 tập trung vào phân tích thành phần tri thức, xác định quan hệ, xây dựng mô hình biểu diễn và tổ chức cơ sở tri thức trên máy tính. **Hiện tại repository chỉ có cấu trúc và các file placeholder; chưa có dữ liệu tri thức hoặc chương trình xử lý.**

## 2. Thành viên

| Họ tên | MSSV | Trách nhiệm chính |
|---|---|---|
| Đoàn Hữu Gia Bình | 24520192 | Phân tích Concepts, Attributes, Facts; chuẩn hóa tri thức thực phẩm, nhóm thực phẩm, thành phần dinh dưỡng và dữ liệu mẫu. |
| Nguyễn Thái Bảo | 24520173 | Phân tích Relations, xác định ràng buộc, xây dựng sơ đồ tri thức tổng thể và tích hợp báo cáo. |
| Võ Hoài Chiều | 24520220 | Thiết kế mô hình biểu diễn tri thức, Rules IF–THEN, điều kiện và kết luận suy luận. |
| Bùi Huy Chương | 24520230 | Tổ chức cơ sở tri thức trên máy, xây dựng chương trình Python đọc/kiểm tra/truy vấn tri thức, kiểm thử và đóng gói. |

## 3. Mô hình biểu diễn tri thức

Mô hình lựa chọn là **Concepts – Attributes – Relations – Facts – Rules**:

| Thành phần | Vai trò trong mô hình dự kiến |
|---|---|
| Concepts | Định nghĩa các lớp đối tượng: thực phẩm, nhóm thực phẩm, chất dinh dưỡng, món ăn, bữa ăn, thực đơn, người dùng. |
| Attributes | Mô tả thuộc tính và kiểu dữ liệu của từng Concept. |
| Relations | Định nghĩa quan hệ giữa các Concepts, miền xác định, miền giá trị và ràng buộc. |
| Facts | Biểu diễn các thực thể, giá trị thuộc tính và quan hệ cụ thể đã biết. |
| Rules | Biểu diễn luật IF–THEN để suy ra tri thức từ các Facts. |

Concepts và Attributes quy định cấu trúc đối tượng; Relations quy định cách liên kết đối tượng. Facts sẽ tuân theo các định nghĩa đó, còn Rules sẽ sử dụng Facts làm tiền đề và tạo kết luận phù hợp với mô hình. Các định nghĩa và dữ kiện cụ thể sẽ được bổ sung ở giai đoạn tiếp theo.

## 4. Cấu trúc repository

Cây thư mục nội dung dự án (không hiển thị thư mục quản lý phiên bản `.git/`):

```text
CS217-FoodNutritionKB/
├── kb/
│   ├── concepts.json
│   ├── facts.json
│   ├── relations.json
│   └── rules.json
├── docs/
│   ├── concepts.md
│   ├── relations.md
│   └── rules.md
├── src/
│   ├── validate_kb.py
│   └── demo_queries.py
├── tests/
│   └── test_cases.md
└── README.md
```

`kb/` dành cho tri thức JSON; `docs/` dành cho tài liệu phân tích; `src/` dành cho chương trình Python; `tests/` dành cho đặc tả tình huống kiểm thử.

## 5. Giải thích từng file

Các chức năng trong bảng là kế hoạch triển khai. Bốn file JSON hiện chỉ chứa `{}`; các file Python và Markdown ngoài README đang để trống.

| Đường dẫn | Chức năng dự kiến | Thành viên phụ trách | Trạng thái |
|---|---|---|---|
| `kb/concepts.json` | Lưu Concepts và Attributes: tên, thuộc tính, kiểu dữ liệu và cấu trúc biểu diễn. | Đoàn Hữu Gia Bình | Placeholder – Chưa triển khai |
| `kb/facts.json` | Lưu thực thể và dữ kiện về thực phẩm, dinh dưỡng, người dùng, món ăn và quan hệ đã biết. | Đoàn Hữu Gia Bình; phối hợp các thành viên liên quan | Placeholder – Chưa triển khai |
| `kb/relations.json` | Lưu Relations, miền xác định, miền giá trị và ràng buộc. | Nguyễn Thái Bảo | Placeholder – Chưa triển khai |
| `kb/rules.json` | Lưu luật IF–THEN, điều kiện, kết luận và mức độ ưu tiên. | Võ Hoài Chiều | Placeholder – Chưa triển khai |
| `docs/concepts.md` | Bảng phân tích khái niệm, thuộc tính và nguồn tri thức. | Đoàn Hữu Gia Bình | Placeholder – Chưa triển khai |
| `docs/relations.md` | Bảng quan hệ, cú pháp, ý nghĩa, tính chất và ràng buộc; bổ sung sơ đồ tri thức sau. | Nguyễn Thái Bảo | Placeholder – Chưa triển khai |
| `docs/rules.md` | Bảng đặc tả mã luật, nội dung, tiền đề, kết luận, Concepts và Relations liên quan. | Võ Hoài Chiều | Placeholder – Chưa triển khai |
| `src/validate_kb.py` | Kiểm tra định dạng JSON, cấu trúc dữ liệu và tính nhất quán của tham chiếu. | Bùi Huy Chương | Placeholder – Chưa triển khai |
| `src/demo_queries.py` | Nạp cơ sở tri thức, truy vấn và minh họa suy luận. | Bùi Huy Chương; phối hợp Võ Hoài Chiều | Placeholder – Chưa triển khai |
| `tests/test_cases.md` | Đặc tả tình huống kiểm thử, đầu vào, kết quả mong đợi và kết quả thực tế. | Bùi Huy Chương | Placeholder – Chưa triển khai |
| `README.md` | Giới thiệu repository, nhóm, mô hình, cấu trúc và phân công công việc. | Cả nhóm; Nguyễn Thái Bảo tích hợp báo cáo | Đã hoàn thiện tài liệu khởi tạo |
