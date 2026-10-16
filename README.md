# Hệ thống tư vấn dinh dưỡng và gợi ý thực đơn

Bài thực hành 2 — Nhóm 1, môn Các hệ cơ sở tri thức (CS217.R11).

## Thành viên và phân công

| Thành viên | MSSV | Phần phụ trách |
|---|---|---|
| Đoàn Hữu Gia Bình | 24520192 | Concepts, Attributes, Facts và nguồn dữ liệu |
| Nguyễn Thái Bảo | 24520173 | Relations, ràng buộc, sơ đồ và tích hợp báo cáo |
| Võ Hoài Chiều | 24520220 | Mô hình biểu diễn và Rules IF–THEN |
| Bùi Huy Chương  | 24520230 | Python nạp/kiểm tra/truy vấn, kiểm thử và đóng gói |

## Mô hình và các tệp

Mô hình **Concepts–Attributes–Relations–Facts–Rules**: Concepts định nghĩa loại đối tượng, Attributes quy định thuộc tính, Relations định nghĩa liên kết; Facts lưu đối tượng và liên kết cụ thể, Rules suy ra kết luận từ Facts.

| Tệp | Nội dung |
|---|---|
| [kb/concepts.json](kb/concepts.json) | 10 Concepts, mỗi Concept có 3–6 thuộc tính, kiểu và ràng buộc |
| [kb/relations.json](kb/relations.json) | 12 Relations: cú pháp, miền, miền giá trị, bội số, ràng buộc |
| [kb/facts.json](kb/facts.json) | `entities`, 572 `edges` khẳng định, 11 `negative_edges` phủ định và danh mục 15 `sources` |
| [kb/rules.json](kb/rules.json) | 14 luật IF–THEN (đặc tả + trường `exec` để thực thi), nguồn, ưu tiên và thứ tự xử lý |
| [docs/concepts.md](docs/concepts.md) | Bảng Concepts, Attributes và cách đọc Facts |
| [docs/relations.md](docs/relations.md) | Bảng Relations, ràng buộc và sơ đồ tổng thể |
| [docs/rules.md](docs/rules.md) | Bảng Rules và cách giải thích kết luận |
| [docs/model.md](docs/model.md) | Bước 3: mô tả hình thức của mô hình, ánh xạ Concepts/Relations, phân loại luật, sơ đồ, ví dụ |
| [docs/kb_organization.md](docs/kb_organization.md) | Bước 4: tổ chức CSTT trên máy, định dạng tệp, cú pháp `exec`, cách mở rộng và chạy |
| [src/](src) | `kb_loader.py` nạp CSTT, `validate_kb.py` kiểm tra, `engine.py` suy diễn tiến, `explain.py` giải thích, `demo_queries.py` CLI, `package_kb.py` đóng gói |
| [tests/test_cases.md](tests/test_cases.md) | 14 ca kiểm thử: đầu vào, kỳ vọng, kết quả thực tế do chương trình ghi |
| [tests/](tests) | 68 unit test (`test_cases_md.py`, `test_validate.py`, `test_engine.py`) |

Dữ liệu gồm **30 thực phẩm, 6 nhóm, 6 chất dinh dưỡng, 5 tác nhân dị ứng, 12 món có định lượng, 15 bữa cụ thể thuộc 3 loại, 5 thực đơn, 7 hồ sơ giả lập và 3 chế độ ăn**. Có 180 bản ghi hàm lượng: 179 giá trị đã biết và 1 giá trị `null`.

Để dùng các tệp sẵn có, dữ liệu tương ứng `foods.json` và `dishes.json` trong phân công được lưu chung tại `facts.entities.food` và `facts.entities.dish`.

R07 là luật ưu tiên dinh dưỡng tổng quát, nhận ba mục tiêu protein/chất xơ/canxi qua bảng ánh xạ. Repo có 14 luật đánh số liên tục từ R01 đến R14.

## Quy ước sử dụng

- ID tiếng Anh `snake_case`; luật dùng mã `R01`–`R14`. Liên kết dùng `subject_id` và `object_id`.
- Dinh dưỡng theo 100 g phần ăn được, đúng `food_state`; đơn vị lấy từ Nutrient. Nguồn và ID bản ghi gốc được giữ để tra cứu.
- Thiếu dữ liệu là `unknown`/`null`. Dị ứng, cần tránh và chế độ ăn được xét trước mục tiêu/sở thích.
- Một nhóm chính/Food, một chế độ chính/User và ba bữa/Menu một ngày là lựa chọn thiết kế của nhóm.
- Hồ sơ là giả lập; phạm vi dị ứng gồm 5 tác nhân trong bài. `eligible_in_model` nghĩa là đạt các điều kiện đã mô hình hóa.

## Trạng thái triển khai

JSON là dữ liệu và đặc tả; mỗi luật có thêm trường `exec` để bộ máy suy diễn thực thi, nên thêm luật cùng loại không cần sửa mã.

- [x] Nạp 4 JSON, kiểm tra theo `concepts.attributes` và `relations` — [src/kb_loader.py](src/kb_loader.py), [src/validate_kb.py](src/validate_kb.py) (Karry)
- [x] Triển khai luật theo `evaluation_plan`: suy diễn tiến, lặp tới điểm cố định, xếp hạng — [src/engine.py](src/engine.py) (Karry)
- [x] Cơ chế giải thích: mã luật, Facts tiền đề, đường lan truyền — [src/explain.py](src/explain.py) (Karry)
- [x] Truy vấn và demo với 7 hồ sơ mẫu — [src/demo_queries.py](src/demo_queries.py) (Karry)
- [x] Kiểm thử: `actual_result` của 14 ca do chương trình ghi (14/14 PASS ngày 2026-10-16); 68 unit test đạt (Karry)
- [x] Đóng gói ZIP kèm bằng chứng chạy thử — [src/package_kb.py](src/package_kb.py) (Karry)
- [x] Tài liệu tổ chức CSTT trên máy (bước 4) — [docs/kb_organization.md](docs/kb_organization.md) (Karry)
- [x] Luật bổ sung R10–R14 (năng lượng theo DGA 2020–2025, giảm cân an toàn, cân bằng nhóm) và 2 hồ sơ `user_an`, `user_tam` — Karry; **cần Chiều và Bình duyệt** vì có thêm dữ liệu vào `rules.json`, `concepts.json`, `facts.json`
- [x] Tài liệu mô hình biểu diễn (bước 3) — [docs/model.md](docs/model.md); Karry viết hỗ trợ, **cần Võ Hoài Chiều duyệt**
- [ ] Báo cáo PDF 4–6 trang `CS217_TH2_Nhom1_BaoCao.pdf` — tích hợp báo cáo: Nguyễn Thái Bảo
- [ ] PDF phân công công việc `CS217_TH2_Nhom1_PhanCong.pdf` — chưa giao người cụ thể
- [ ] Nhóm duyệt và nộp `dist/CS217_TH2_Nhom1_KnowledgeBase.zip`

## Cách chạy

Cần Python 3.10 trở lên; không cần cài thêm thư viện. Chạy tại thư mục gốc của repo:

```bash
python src/validate_kb.py                         # kiểm tra CSTT: 0 lỗi -> HỢP LỆ
python src/demo_queries.py demo                   # kịch bản minh họa đầy đủ
python src/demo_queries.py users                  # danh sách hồ sơ mẫu
python src/demo_queries.py lookup food_rice_cooked
python src/demo_queries.py check user_minh menu_ordinary          # trạng thái + giải thích
python src/demo_queries.py recommend user_an --level menu         # gợi ý thực đơn có xếp hạng
python src/demo_queries.py compare user_minh dish_rice_chicken dish_chickpea_salad
python -m unittest discover -s tests              # 68 test (hoặc: python -m pytest tests)
python tests/update_case_results.py               # chạy 14 ca và ghi actual_result vào tests/test_cases.md
python src/package_kb.py                          # tạo dist/CS217_TH2_Nhom1_KnowledgeBase.zip
```

Thêm `--json` vào các lệnh của `demo_queries.py` để nhận kết quả dạng JSON. Cách thêm thực phẩm, món, hồ sơ hoặc luật mới xem [docs/kb_organization.md](docs/kb_organization.md).

> Kết quả chỉ mang tính tham khảo trong phạm vi tri thức đã mô hình hóa, không thay thế tư vấn của bác sĩ hoặc chuyên gia dinh dưỡng.
