# Concepts, Attributes và Facts

Định nghĩa nằm trong [concepts.json](../kb/concepts.json); đối tượng cụ thể nằm trong [facts.json](../kb/facts.json).
Concept `food` là loại đối tượng; `food_rice_cooked` là một đối tượng thuộc loại đó.

## Bảng Concepts

Nguồn chung của bảng: `source_th1`, `source_th2`, `source_design`; tra mục `sources` trong Facts. Cột Facts là ID ví dụ có thật.

| Concept | Ý nghĩa | Cú pháp | Ký hiệu ví dụ | Facts | Rules |
| --- | --- | --- | --- | --- | --- |
| `food` | Thực phẩm hoặc nguyên liệu, phân biệt theo trạng thái bản ghi. | `food(id)` | `food(food_rice_cooked)` | `food_rice_cooked` | R01, R02, R03, R04, R05, R06, R07, R08, R09, R10 |
| `food_group` | Nhóm phân loại chính do bài thiết kế; không phải ngưỡng giàu chất. | `food_group(id)` | `food_group(group_starch)` | `group_starch` | — |
| `nutrient` | Đại lượng dinh dưỡng; năng lượng được đưa chung vào danh mục theo yêu cầu. | `nutrient(id)` | `nutrient(nutrient_protein)` | `nutrient_protein` | R06, R07, R08 |
| `nutrient_content` | Bản ghi hàm lượng của một food và một nutrient. | `nutrient_content(id)` | `nutrient_content(nc_rice_cooked_protein)` | `nc_rice_cooked_protein` | R05, R06, R07, R08 |
| `allergen` | Tác nhân dị ứng trong danh mục 5 của bài. | `allergen(id)` | `allergen(allergen_milk)` | `allergen_milk` | R01 |
| `dish` | Công thức phối hợp các nguyên liệu đã ở đúng trạng thái trong Food. | `dish(id)` | `dish(dish_rice_chicken)` | `dish_rice_chicken` | R02, R05, R06, R07, R08, R09, R10 |
| `meal` | Bữa ăn cụ thể; breakfast/lunch/dinner là loại, không phải ID bữa. | `meal(id)` | `meal(meal_ordinary_breakfast)` | `meal_ordinary_breakfast` | R02, R06, R07, R08, R09, R10 |
| `menu` | Thực đơn một ngày trong phạm vi thiết kế này. | `menu(id)` | `menu(menu_ordinary)` | `menu_ordinary` | R02, R06, R07, R08, R09, R10 |
| `user_profile` | Hồ sơ đầu vào giả lập; các khai báo không phải tri thức chuyên môn. | `user_profile(id)` | `user_profile(user_minh)` | `user_minh` | R01, R03, R04, R05, R07, R08, R09, R10 |
| `diet_pattern` | Định nghĩa chế độ ăn được chọn cho bài. | `diet_pattern(id)` | `diet_pattern(diet_vegan)` | `diet_vegan` | R03, R05 |

## Attributes và kiểu dữ liệu

Mỗi Concept có 3–6 thuộc tính nghiệp vụ; tất cả bắt buộc có khóa. `_meta` lưu thông tin nguồn dùng chung, không tính vào số thuộc tính.

| Concept | Thuộc tính: kiểu và điều kiện |
| --- | --- |
| `food` | `id`: string<br>`name`: string<br>`food_state`: string<br>`origin`: string {plant, dairy, egg, meat, seafood, unknown}<br>`allergen_status`: string {complete, unknown}<br>`diet_status`: string {complete, unknown} |
| `food_group` | `id`: string<br>`name`: string<br>`criterion`: string |
| `nutrient` | `id`: string<br>`name`: string<br>`unit`: string {kcal, g, mg}<br>`usda_nutrient_id`: integer ≥1 |
| `nutrient_content` | `id`: string<br>`value`: number/null ≥0<br>`basis_g`: number = 100 g<br>`status`: string {known, unknown}<br>`source_id`: string<br>`source_record_id`: string/null |
| `allergen` | `id`: string<br>`name`: string<br>`description`: string |
| `dish` | `id`: string<br>`name`: string<br>`servings`: integer ≥1<br>`recipe_status`: string {complete, unknown} |
| `meal` | `id`: string<br>`name`: string<br>`meal_type`: string {breakfast, lunch, dinner} |
| `menu` | `id`: string<br>`name`: string<br>`scope`: string = one_day |
| `user_profile` | `id`: string<br>`name`: string<br>`context`: object (age:integer≥18; sex:string{female,male,unspecified}; activity:string{low,moderate,high}; đủ các trường)<br>`nutrition_goal`: string {prefer_protein, prefer_fiber, prefer_calcium, none}<br>`allergy_status`: string {complete, unknown}<br>`avoid_status`: string {complete, unknown} |
| `diet_pattern` | `id`: string<br>`name`: string<br>`policy_description`: string<br>`policy_status`: string {complete, unknown} |

## Facts và nguồn

| Vị trí trong facts.entities | Số lượng |
| --- | --- |
| `food` | 30 |
| `food_group` | 6 |
| `nutrient` | 6 |
| `nutrient_content` | 180 |
| `allergen` | 5 |
| `dish` | 12 |
| `meal` | 15 |
| `menu` | 5 |
| `user_profile` | 5 |
| `diet_pattern` | 3 |

`edges` lưu quan hệ khẳng định; `negative_edges` lưu phủ định tường minh. Mỗi cạnh có `id`, `relation`, `subject_id`, `object_id`, `attributes` và `_meta.source_ids`. ID phải duy nhất, đầu mút đúng Concept và bội số trong Relations.

Ví dụ một sự kiện thuộc nhóm:

```json
{
  "id": "fact_0001",
  "relation": "belongs_to_group",
  "subject_id": "food_rice_cooked",
  "object_id": "group_starch",
  "attributes": {},
  "_meta": {
    "source_ids": [
      "source_design"
    ]
  }
}
```

NutrientContent liên kết với Food qua `has_nutrient_content` và Nutrient qua `measures_nutrient`, duy nhất theo cặp Food–Nutrient. 30 Food × 6 Nutrient tạo 180 bản ghi.

- `value` tính trên `basis_g=100` g phần ăn được, đúng trạng thái `food_state`. Đơn vị: năng lượng kcal; protein/lipid/carbohydrate/chất xơ g; canxi mg.
- `status=known` cần giá trị không âm và `source_record_id`. `status=unknown` giữ `value=null`; không đổi thành 0. Hiện chất xơ của `food_shrimp_cooked` chưa có giá trị.
- Nguồn dinh dưỡng: USDA SR Legacy 2018. `Food._meta.fdc_id` là mã thực phẩm, `source_description` là mô tả gốc; `Nutrient.usda_nutrient_id` là mã chất, `NutrientContent.source_record_id` là mã dòng giá trị.
- Dị ứng/chế độ ăn dẫn nguồn FDA/NHS; nhóm thực phẩm, công thức và bội số là thiết kế của nhóm. Hồ sơ người dùng là dữ liệu giả lập.
- `complete` chỉ xác nhận đã đánh giá hết danh mục trong bài (5 tác nhân, 3 chế độ); `unknown` giữ trạng thái chưa biết. Các chế độ: thông thường, chay lacto-ovo (có trứng/sữa), thuần chay.

Công thức sử dụng khối lượng nguyên liệu ở đúng trạng thái bản ghi; không tự tính biến đổi khi nấu. 15 Meal là các bữa cụ thể thuộc 3 loại `breakfast/lunch/dinner`; Menu mẫu có phạm vi `one_day`.
