# Rules IF–THEN

[rules.json](../kb/rules.json) chứa 14 đặc tả khai báo (R10–R14 bổ sung cho năng lượng, giảm cân và cân bằng nhóm). `if_all` nghĩa là thỏa tất cả điều kiện; `if_any` nghĩa là thỏa ít nhất một; `then` mô tả kết luận/hành động. Mỗi luật có thêm trường `exec` để [src/engine.py](../src/engine.py) thực thi; cú pháp `exec` xem [kb_organization.md](kb_organization.md).

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
| R07 | soft / 20 | Mục tiêu ánh xạ tới chất dinh dưỡng n; x,y cùng Concept, đủ điều kiện, cùng cơ sở tính; N(x,n), N(y,n) đều known và N(x,n)>N(y,n). | Ưu tiên x hơn y theo chất n. | user_profile, food, dish, meal, menu, nutrient, nutrient_content | REL02, REL03, REL04, REL09, REL10 | source_th1, source_design |
| R08 | soft / 10 | Ứng viên đủ điều kiện; không có mục tiêu hoặc đồng hạng mục tiêu. | Tính +1/thích, −1/không thích, 0/chưa khai báo; mỗi Food tính một lần. | user_profile, food, dish, meal, menu | REL12, REL04, REL09, REL10 | source_th2, source_design |
| R09 | hard / 80 | Cấu trúc hợp lệ, đủ dữ liệu và kiểm tra cứng/lan truyền đã ổn định, không rejected/requires_review. | eligible_in_model; xếp mục tiêu giảm dần, sở thích giảm dần, độ phủ nhóm (R14, chỉ Menu) giảm dần, ID tăng dần. | user_profile, food, dish, meal, menu | REL04, REL09, REL10, REL07, REL08 | source_th2, source_design |
| R10 | calculation / 65 | Biết tuổi, giới (female/male) và mức vận động của người dùng. | energy_requirement (kcal/ngày) tra bảng DGA Table A2-2; low/moderate/high = Sedentary/Moderately Active/Active; giới chưa rõ → null. | user_profile | — | source_dga_energy, source_design |
| R11 | calculation / 60 | Đã có energy_requirement (R10). | energy_target = max(EER − 500, sàn 1200 nữ/1500 nam) nếu lose_weight, ngược lại = EER; Menu: tỷ lệ năng lượng/mục tiêu (chỉ hiển thị). | user_profile, menu, nutrient | REL02, REL03, REL04, REL09, REL10 | source_aha_2013, source_design |
| R12 | hard / 90 | Mục tiêu lose_weight và (thiếu cân nặng/chiều cao, hoặc BMI < 25, hoặc giới chưa rõ). | requires_review mọi food (R02 lan truyền); lý do weight_loss_not_supported kèm BMI hoặc trường thiếu. | user_profile, food | — | source_who_bmi, source_aha_2013, source_design |
| R13 | soft / 20 | Mục tiêu lose_weight; hai ứng viên cùng cấp, đủ điều kiện, cùng cơ sở tính. | Menu: ưu tiên năng lượng gần energy_target hơn; Food/Dish/Meal: ưu tiên năng lượng thấp hơn. | user_profile, food, dish, meal, menu, nutrient, nutrient_content | REL02, REL03, REL04, REL09, REL10 | source_aha_2013, source_design |
| R14 | soft / 5 | Hai Menu đủ điều kiện, đồng hạng mục tiêu và sở thích. | Ưu tiên Menu phủ nhiều nhóm hơn trong 6 nhóm; bỏ group_dairy khi thuần chay hoặc dị ứng sữa; ghi nhóm thiếu. | user_profile, menu, food, food_group, diet_pattern, allergen | REL01, REL04, REL09, REL10, REL07, REL06 | source_dga_food_groups, source_design |


## Luật ưu tiên dinh dưỡng tổng quát R07

Repo có 14 luật đánh số liên tục từ R01 đến R14. Không thêm Concept hoặc Relation: nutrient_of_goal là phép tra cấu hình trong `exec.then.goals`.

| nutrition_goal | Chất dinh dưỡng n | Hướng so sánh |
|---|---|---|
| prefer_protein | nutrient_protein | desc: hàm lượng cao hơn |
| prefer_fiber | nutrient_fiber | desc: hàm lượng cao hơn |
| prefer_calcium | nutrient_calcium | desc: hàm lượng cao hơn |

IF mục tiêu của người dùng ánh xạ tới n; hai ứng viên cùng Concept, đủ điều kiện, cùng cơ sở tính; cả hai giá trị đã biết và N(x,n)>N(y,n), THEN ưu tiên x hơn y. R05 vẫn chặn khi thiếu chất cần so; luật cứng vẫn được xét trước.

Thêm mục tiêu ưu tiên chất khác bằng cách khai báo giá trị mục tiêu hợp lệ trong Concepts và ánh xạ `nutrition_goal → nutrient/direction` trong R07; không phải viết thêm luật cùng cấu trúc hay sửa engine.

## Thứ tự xử lý và xung đột

Theo `evaluation_plan`: kiểm tra cấu trúc → ràng buộc cứng và lan truyền tới khi trạng thái không đổi → tổng hợp dinh dưỡng → xác nhận đủ điều kiện → xếp hạng.

Không chạy đơn thuần theo số mã hoặc priority toàn cục: R09 xác nhận đủ điều kiện trước R07 và R08. Trong cùng pha, priority lớn được xét trước. Thứ tự trạng thái: `rejected` > `requires_review` > `eligible_in_model`; ràng buộc cứng luôn thắng ưu tiên mềm.

Chỉ so ứng viên cùng Concept: Food/100 g, Dish/khẩu phần, Meal/toàn bữa, Menu/toàn ngày. R07 là so sánh tương đối theo mục tiêu đã chọn.

R10–R11 chạy ở pha aggregation sau R06 (priority 65, 60); R12 thuộc pha ràng buộc cứng như R05. Trong pha ranking, R07/R13 cùng priority 20 nhưng mỗi hồ sơ chỉ có một `nutrition_goal` nên chỉ một luật áp dụng; sau đó R08 (10), R14 (5), cuối cùng ID tăng dần.

## Công thức R06

- Tổng món: `Σ amount_g × value_per_100g / 100`.
- Một khẩu phần món: tổng món chia `dish.servings`.
- Bữa ăn: `Σ servings_trên_cạnh_contains_dish × dinh_dưỡng_mỗi_khẩu_phần`.
- Thực đơn: tổng các bữa.

Giá trị cần dùng chưa biết thì kết quả chất đó là `null` kèm danh sách đầu vào thiếu. Không thay `null` bằng 0.

## Công thức R10–R14

- R10: `energy_requirement(u)` = ô của bảng DGA 2020–2025 Table A2-2 ứng với giới, nhóm tuổi và cột vận động của `u`. Ví dụ `user_an` (nữ, 35 tuổi, low) → hàng nữ 31–35, cột Sedentary → 1800 kcal/ngày.
- R11: `lose_weight` → `energy_target = max(energy_requirement − 500, 1200 nữ | 1500 nam)`; mục tiêu khác → `energy_target = energy_requirement`. `energy_ratio(menu) = năng lượng menu / energy_target`. Ví dụ `user_an`: max(1800 − 500, 1200) = 1300.
- R12: `BMI = weight_kg / (height_cm / 100)²`; ngưỡng 25 là tham số trong `exec`, có thể đổi mà không sửa mã.
- R13: điểm Menu = `−|năng lượng − energy_target|`; điểm Food/Dish/Meal = `−năng lượng`; điểm lớn hơn xếp trước.
- R14: điểm = số nhóm cần phủ có mặt trong các food của Menu.

## Giải thích kết luận và kiểm thử

Mỗi kết luận cần lưu mã luật, ID Facts/đối tượng tiền đề, lý do và đường dẫn thành phần. Ví dụ: `user_minh` dị ứng sữa; `food_milk_whole` chứa sữa → R01 loại thực phẩm → R02 truyền qua `dish_oat_milk`, `meal_ordinary_breakfast`, `menu_ordinary`.

`children` là các thành phần lấy qua REL04/REL09/REL10; trạng thái và tổng dinh dưỡng là kết quả suy luận, không thêm Concept hay Relation lưu trữ mới.

Xem [14 ca kiểm thử](../tests/test_cases.md) để có đầu vào và kỳ vọng; `actual_result` do chương trình ghi (14/14 PASS ngày 2026-10-16). Phạm vi `eligible_in_model` giới hạn ở tri thức đã khai báo; Menu mẫu chưa được kiểm chứng đáp ứng nhu cầu dinh dưỡng hằng ngày.
