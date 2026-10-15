# Rules IF–THEN

[rules.json](../kb/rules.json) chứa 10 đặc tả khai báo. `if_all` nghĩa là thỏa tất cả điều kiện; `if_any` nghĩa là thỏa ít nhất một; `then` mô tả kết luận/hành động. Karry cần hiện thực các hành động này trong Python.

## Bảng Rules

`hard` = ràng buộc bắt buộc; `soft` = ưu tiên xếp hạng; `calculation` = tính toán. Nguồn tra trong `facts.sources`; mã REL tra [bảng Relations](relations.md).

| Mã | Loại / ưu tiên | IF | THEN | Concepts (Obj) | Quan hệ | Nguồn |
| --- | --- | --- | --- | --- | --- | --- |
| R01 | hard / 100 | Dị ứng tác nhân a và Food f chứa a. | Loại f: rejected/allergen_match. | user_profile, food, allergen | REL06, REL05 | source_fda, source_design |
| R02 | hard / 95 | Một thành phần bị rejected hoặc requires_review. | Lan truyền lên Dish → Meal → Menu; rejected ưu tiên hơn requires_review. | food, dish, meal, menu | REL04, REL09, REL10 | source_th2, source_design |
| R03 | hard / 100 | Theo chế độ d và đã biết Food f không phù hợp d. | Loại f: rejected/diet_mismatch. | user_profile, diet_pattern, food | REL07, REL08 | source_vegetarian, source_vegan, source_design |
| R04 | hard / 100 | Người dùng khai báo tránh Food f. | Loại f: rejected/explicit_avoid, kể cả khi thích f. | user_profile, food | REL11 | source_th2, source_design |
| R05 | hard / 90 | Thiếu một trong các thông tin dị ứng, tránh, chế độ, nguyên liệu hoặc hàm lượng cần dùng. | requires_review nếu chưa rejected; ghi thông tin thiếu. | user_profile, food, dish, nutrient_content, diet_pattern | REL07, REL08, REL02, REL03, REL04 | source_th2, source_design |
| R06 | calculation / 70 | Hàm lượng đã biết, đúng trạng thái/100 g; định lượng và khẩu phần hợp lệ. | Tính dinh dưỡng món/khẩu phần, bữa và thực đơn; đầu vào thiếu giữ null. | food, nutrient, nutrient_content, dish, meal, menu | REL02, REL03, REL04, REL09, REL10 | source_usda_dictionary, source_design |
| R07 | soft / 20 | Mục tiêu protein; hai ứng viên cùng cấp, đủ điều kiện, cùng cơ sở tính. | Ưu tiên protein cao hơn. | user_profile, food, dish, meal, menu, nutrient, nutrient_content | REL02, REL03, REL04, REL09, REL10 | source_th1, source_design |
| R08 | soft / 20 | Mục tiêu chất xơ hoặc canxi; hai ứng viên cùng cấp, đủ điều kiện, cùng cơ sở tính. | Ưu tiên chất tương ứng cao hơn. | user_profile, food, dish, meal, menu, nutrient, nutrient_content | REL02, REL03, REL04, REL09, REL10 | source_th1, source_design |
| R09 | soft / 10 | Ứng viên đủ điều kiện; không có mục tiêu hoặc đồng hạng mục tiêu. | Tính +1/thích, −1/không thích, 0/chưa khai báo; mỗi Food tính một lần. | user_profile, food, dish, meal, menu | REL12, REL04, REL09, REL10 | source_th2, source_design |
| R10 | hard / 80 | Cấu trúc hợp lệ, đủ dữ liệu và kiểm tra cứng/lan truyền đã ổn định, không rejected/requires_review. | eligible_in_model; xếp mục tiêu giảm dần, sở thích giảm dần, ID tăng dần. | user_profile, food, dish, meal, menu | REL04, REL09, REL10, REL07, REL08 | source_th2, source_design |

## Thứ tự xử lý và xung đột

Theo `evaluation_plan`: kiểm tra cấu trúc → ràng buộc cứng và lan truyền tới khi trạng thái không đổi → tổng hợp dinh dưỡng → xác nhận đủ điều kiện → xếp hạng.

Không chạy đơn thuần theo số mã hoặc priority toàn cục: R10 xác nhận đủ điều kiện trước R07–R09. Trong cùng pha, priority lớn được xét trước. Thứ tự trạng thái: `rejected` > `requires_review` > `eligible_in_model`; ràng buộc cứng luôn thắng ưu tiên mềm.

Chỉ so ứng viên cùng Concept: Food/100 g, Dish/khẩu phần, Meal/toàn bữa, Menu/toàn ngày. R07/R08 là so sánh tương đối theo mục tiêu đã chọn.

## Công thức R06

- Tổng món: `Σ amount_g × value_per_100g / 100`.
- Một khẩu phần món: tổng món chia `dish.servings`.
- Bữa ăn: `Σ servings_trên_cạnh_contains_dish × dinh_dưỡng_mỗi_khẩu_phần`.
- Thực đơn: tổng các bữa.

Giá trị cần dùng chưa biết thì kết quả chất đó là `null` kèm danh sách đầu vào thiếu. Không thay `null` bằng 0.

## Giải thích kết luận và kiểm thử

Mỗi kết luận cần lưu mã luật, ID Facts/đối tượng tiền đề, lý do và đường dẫn thành phần. Ví dụ: `user_minh` dị ứng sữa; `food_milk_whole` chứa sữa → R01 loại thực phẩm → R02 truyền qua `dish_oat_milk`, `meal_ordinary_breakfast`, `menu_ordinary`.

`children` là các thành phần lấy qua REL04/REL09/REL10; trạng thái và tổng dinh dưỡng là kết quả suy luận, không thêm Concept hay Relation lưu trữ mới.

Xem [10 ca kiểm thử](../tests/test_cases.md) để có đầu vào và kỳ vọng. Kết quả thực tế chưa được chạy. Phạm vi `eligible_in_model` giới hạn ở tri thức đã khai báo; Menu mẫu chưa được kiểm chứng đáp ứng nhu cầu dinh dưỡng hằng ngày.
