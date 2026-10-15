# Hệ thống tư vấn dinh dưỡng và gợi ý thực đơn

Bài thực hành 2 — Nhóm 1, môn Các hệ cơ sở tri thức (CS217.R11).

## Thành viên và phân công

| Thành viên | MSSV | Phần phụ trách |
|---|---|---|
| Đoàn Hữu Gia Bình | 24520192 | Concepts, Attributes, Facts và nguồn dữ liệu |
| Nguyễn Thái Bảo | 24520173 | Relations, ràng buộc, sơ đồ và tích hợp báo cáo |
| Võ Hoài Chiều | 24520220 | Mô hình biểu diễn và Rules IF–THEN |
| Bùi Huy Chương (Karry) | 24520230 | Python nạp/kiểm tra/truy vấn, kiểm thử và đóng gói |

## Mô hình và các tệp

Mô hình **Concepts–Attributes–Relations–Facts–Rules**: Concepts định nghĩa loại đối tượng, Attributes quy định thuộc tính, Relations định nghĩa liên kết; Facts lưu đối tượng và liên kết cụ thể, Rules suy ra kết luận từ Facts.

| Tệp | Nội dung |
|---|---|
| [kb/concepts.json](kb/concepts.json) | 10 Concepts, mỗi Concept có 3–6 thuộc tính, kiểu và ràng buộc |
| [kb/relations.json](kb/relations.json) | 12 Relations: cú pháp, miền, miền giá trị, bội số, ràng buộc |
| [kb/facts.json](kb/facts.json) | `entities`, 570 `edges` khẳng định, 11 `negative_edges` phủ định và danh mục `sources` |
| [kb/rules.json](kb/rules.json) | 10 luật IF–THEN, nguồn, ưu tiên và thứ tự xử lý |
| [docs/concepts.md](docs/concepts.md) | Bảng Concepts, Attributes và cách đọc Facts |
| [docs/relations.md](docs/relations.md) | Bảng Relations, ràng buộc và sơ đồ tổng thể |
| [docs/rules.md](docs/rules.md) | Bảng Rules và cách giải thích kết luận |
| [tests/test_cases.md](tests/test_cases.md) | 10 ca kiểm thử: đầu vào, kỳ vọng, kết quả thực tế |

Dữ liệu gồm **30 thực phẩm, 6 nhóm, 6 chất dinh dưỡng, 5 tác nhân dị ứng, 12 món có định lượng, 15 bữa cụ thể thuộc 3 loại, 5 thực đơn, 5 hồ sơ giả lập và 3 chế độ ăn**. Có 180 bản ghi hàm lượng: 179 giá trị đã biết và 1 giá trị `null`.

Để dùng các tệp sẵn có, dữ liệu tương ứng `foods.json` và `dishes.json` trong phân công được lưu chung tại `facts.entities.food` và `facts.entities.dish`.

## Quy ước sử dụng

- ID tiếng Anh `snake_case`; luật dùng mã `R01`–`R10`. Liên kết dùng `subject_id` và `object_id`.
- Dinh dưỡng theo 100 g phần ăn được, đúng `food_state`; đơn vị lấy từ Nutrient. Nguồn và ID bản ghi gốc được giữ để tra cứu.
- Thiếu dữ liệu là `unknown`/`null`. Dị ứng, cần tránh và chế độ ăn được xét trước mục tiêu/sở thích.
- Một nhóm chính/Food, một chế độ chính/User và ba bữa/Menu một ngày là lựa chọn thiết kế của nhóm.
- Hồ sơ là giả lập; phạm vi dị ứng gồm 5 tác nhân trong bài. `eligible_in_model` nghĩa là đạt các điều kiện đã mô hình hóa.

## Trạng thái triển khai

JSON là dữ liệu và đặc tả; các chuỗi IF–THEN chưa tự thực thi. Karry cần nạp 4 JSON, kiểm tra theo `concepts.attributes` và `relations`, sau đó triển khai luật theo `evaluation_plan`.

[src/validate_kb.py](src/validate_kb.py) và [src/demo_queries.py](src/demo_queries.py) đang trống. Chưa có lệnh chạy hoặc kết quả kiểm thử ứng dụng; `actual_result` trong các ca kiểm thử hiện là `null`.

Đầu ra còn cần hoàn thiện theo đề: chương trình Python và bằng chứng chạy thử, báo cáo PDF 4–6 trang, PDF phân công công việc.
