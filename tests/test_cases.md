# Test cases

10 ca dưới đây bao phủ truy vấn, R01–R10, thiếu dữ liệu và ngoại lệ. `input` là đầu vào; `expected` là kết quả cần đạt; `rules` là các luật liên quan; `actual_result` sẽ được điền sau khi chạy.

**Trạng thái chung: chưa thực thi**, do hai tệp Python đang trống. Tất cả `actual_result=null`; kỳ vọng không phải bằng chứng chương trình đã chạy.

Mỗi ca bắt đầu từ dữ liệu gốc. `mutation` chỉ thay đổi bản sao dữ liệu trong bộ nhớ cho ca đó; TC10 áp dụng từng thay đổi riêng, không sửa Facts gốc. `override_goal` thay mục tiêu trên bản sao hồ sơ.

## TC01 — Tra cứu nhóm và protein của cơm

```json
{
  "id": "TC01",
  "input": {
    "food_id": "food_rice_cooked",
    "query": ["belongs_to_group", "nutrient_protein"]
  },
  "expected": {
    "group_id": "group_starch",
    "protein_per_100g": 2.69,
    "unit": "g"
  },
  "rules": [],
  "actual_result": null
}
```

## TC02 — Dị ứng đậu phộng trực tiếp

```json
{
  "id": "TC02",
  "input": {
    "user_id": "user_huy",
    "food_id": "food_peanut_roasted"
  },
  "expected": {
    "status": "rejected",
    "reason": "allergen_match",
    "allergen_id": "allergen_peanut"
  },
  "rules": ["R01"],
  "actual_result": null
}
```

## TC03 — Lan truyền dị ứng sữa từ food tới dish/menu

```json
{
  "id": "TC03",
  "input": {
    "user_id": "user_minh",
    "dish_id": "dish_oat_milk",
    "menu_id": "menu_ordinary"
  },
  "expected": {
    "dish_status": "rejected",
    "menu_status": "rejected",
    "path": ["food_milk_whole", "dish_oat_milk", "meal_ordinary_breakfast", "menu_ordinary"]
  },
  "rules": ["R01", "R02"],
  "actual_result": null
}
```

## TC04 — Người thuần chay loại món có trứng/bơ sữa

```json
{
  "id": "TC04",
  "input": {
    "user_id": "user_quang",
    "dish_id": "dish_egg_potato"
  },
  "expected": {
    "status": "rejected",
    "reason": "diet_mismatch"
  },
  "rules": ["R03", "R02"],
  "actual_result": null
}
```

## TC05 — Cần tránh thắng sở thích

```json
{
  "id": "TC05",
  "input": {
    "user_id": "user_quang",
    "dish_id": "dish_rice_chicken"
  },
  "expected": {
    "status": "rejected",
    "reason_codes": ["explicit_avoid", "diet_mismatch"],
    "preference_cannot_restore": true
  },
  "rules": ["R03", "R04", "R02", "R09"],
  "actual_result": null
}
```

## TC06 — Tổng hợp 6 hàm lượng của công thức/khẩu phần

```json
{
  "id": "TC06",
  "input": {
    "dish_id": "dish_rice_chicken"
  },
  "expected": {
    "servings": 1,
    "nutrients_per_serving": {
      "nutrient_energy": 439.2,
      "nutrient_protein": 37.435,
      "nutrient_lipid": 9.4,
      "nutrient_carbohydrate": 49.435,
      "nutrient_fiber": 3.9,
      "nutrient_calcium": 70.05
    },
    "tolerance": 0.0001
  },
  "rules": ["R06"],
  "actual_result": null
}
```

## TC07 — Xếp hạng protein trên hai món eligible

```json
{
  "id": "TC07",
  "input": {
    "user_id": "user_minh",
    "dish_ids": ["dish_rice_chicken", "dish_chickpea_salad"]
  },
  "expected": {
    "order": ["dish_rice_chicken", "dish_chickpea_salad"],
    "protein_g": {
      "dish_rice_chicken": 37.435,
      "dish_chickpea_salad": 14.514
    }
  },
  "rules": ["R05", "R10", "R06", "R07"],
  "actual_result": null
}
```

## TC08 — Mục tiêu chất xơ/canxi và sở thích

```json
{
  "id": "TC08",
  "input": {
    "subcases": [
      {
        "user_id": "user_lan",
        "dish_ids": ["dish_lentil_potato", "dish_chickpea_salad"],
        "metric": "nutrient_fiber"
      },
      {
        "user_id": "user_minh",
        "override_goal": "prefer_calcium",
        "dish_ids": ["dish_rice_tofu", "dish_chickpea_salad"],
        "metric": "nutrient_calcium"
      },
      {
        "user_id": "user_huy",
        "dish_ids": ["dish_rice_chicken", "dish_rice_tofu"],
        "metric": "preference"
      }
    ]
  },
  "expected": {
    "fiber_order": ["dish_lentil_potato", "dish_chickpea_salad"],
    "calcium_order": ["dish_rice_tofu", "dish_chickpea_salad"],
    "preference_order": ["dish_rice_chicken", "dish_rice_tofu"],
    "preference_scores": {
      "dish_rice_chicken": 1,
      "dish_rice_tofu": -1
    }
  },
  "rules": ["R06", "R08", "R09", "R10"],
  "actual_result": null
}
```

## TC09 — Thiếu dữ liệu không suy đủ điều kiện

```json
{
  "id": "TC09",
  "input": {
    "subcases": [
      {
        "user_id": "user_vy",
        "dish_id": "dish_fruit_plate"
      },
      {
        "user_id": "user_minh",
        "food_id": "food_whole_wheat_bread"
      },
      {
        "user_id": "user_minh",
        "dish_id": "dish_rice_chicken",
        "mutation": {
          "target": "nc_chicken_roasted_protein",
          "set": {
            "status": "unknown",
            "value": null,
            "source_record_id": null
          }
        }
      }
    ]
  },
  "expected": {
    "statuses": ["requires_review", "requires_review", "requires_review"],
    "null_not_zero": true
  },
  "rules": ["R05", "R02", "R06", "R10"],
  "actual_result": null
}
```

## TC10 — Ngoại lệ tham chiếu, định lượng và phủ định mâu thuẫn

```json
{
  "id": "TC10",
  "input": {
    "mutations_separately": [
      {
        "operation": "replace_ingredient_object",
        "dish_id": "dish_rice_chicken",
        "new_food_id": "food_missing"
      },
      {
        "operation": "set_amount_g",
        "dish_id": "dish_rice_chicken",
        "food_id": "food_chicken_roasted",
        "value": 0
      },
      {
        "operation": "add_negative_edge",
        "relation": "contains_allergen",
        "subject_id": "food_milk_whole",
        "object_id": "allergen_milk"
      }
    ]
  },
  "expected": {
    "validation_errors": ["dangling_reference", "non_positive_amount", "positive_negative_conflict"],
    "inference_not_started": true
  },
  "rules": [],
  "actual_result": null
}
```
