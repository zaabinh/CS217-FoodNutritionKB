# Test cases

14 ca dưới đây bao phủ truy vấn, các luật đang dùng R01–R14, thiếu dữ liệu và ngoại lệ (TC11–TC14 bổ sung cho R10–R14). `input` là đầu vào; `expected` là kết quả cần đạt; `rules` là các luật liên quan; `actual_result` sẽ được điền sau khi chạy.

**Trạng thái chung: đã thực thi ngày 2026-10-16 — 14/14 PASS.** `actual_result` do `python tests/update_case_results.py` ghi tự động từ kết quả chương trình, không chép tay; `python -m unittest discover -s tests` chạy lại cùng các ca này.

Mỗi ca bắt đầu từ dữ liệu gốc. `mutation` chỉ thay đổi bản sao dữ liệu trong bộ nhớ cho ca đó; TC10 áp dụng từng thay đổi riêng, không sửa Facts gốc. `override_goal` thay mục tiêu trên bản sao hồ sơ; `override_context` gán và `remove_context` xóa trường trong `context` của bản sao hồ sơ.

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
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {"group_id": "group_starch", "protein_per_100g": 2.69, "unit": "g"}
  }
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
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "status": "rejected",
      "reasons": ["allergen_match"],
      "allergen_ids": ["allergen_peanut"],
      "rules_fired": ["R01"]
    }
  }
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
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "dish_status": "rejected",
      "menu_status": "rejected",
      "path": ["food_milk_whole", "dish_oat_milk", "meal_ordinary_breakfast", "menu_ordinary"],
      "rules_fired": ["R01", "R02"]
    }
  }
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
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "status": "rejected",
      "reasons": ["diet_mismatch"],
      "origins": ["food_butter_unsalted", "food_egg_boiled"],
      "rules_fired": ["R02", "R03"]
    }
  }
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
  "rules": ["R03", "R04", "R02", "R08"],
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "status": "rejected",
      "reason_codes": ["diet_mismatch", "explicit_avoid"],
      "liked_foods": ["food_chicken_roasted"],
      "in_ranking": false,
      "notes": ["avoid_overrides_like [fact_0561]"],
      "rules_fired": ["R02", "R03", "R04"],
      "preference_cannot_restore": true
    }
  }
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
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "servings": 1,
      "basis": "per_serving",
      "nutrients_per_serving": {
        "nutrient_energy": 439.2,
        "nutrient_protein": 37.435,
        "nutrient_lipid": 9.4,
        "nutrient_carbohydrate": 49.435,
        "nutrient_fiber": 3.9,
        "nutrient_calcium": 70.05
      }
    }
  }
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
  "rules": ["R05", "R09", "R06", "R07"],
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "order": ["dish_rice_chicken", "dish_chickpea_salad"],
      "criteria": ["R07", "R08"],
      "protein_g": {"dish_rice_chicken": 37.435, "dish_chickpea_salad": 14.514},
      "decided_by": ["R07"]
    }
  }
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
  "rules": ["R06", "R07", "R08", "R09"],
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "fiber_order": ["dish_lentil_potato", "dish_chickpea_salad"],
      "fiber_order_decided_by": ["R07"],
      "calcium_order": ["dish_rice_tofu", "dish_chickpea_salad"],
      "calcium_order_decided_by": ["R07"],
      "preference_order": ["dish_rice_chicken", "dish_rice_tofu"],
      "preference_order_decided_by": ["R08"],
      "preference_scores": {"dish_rice_chicken": 1, "dish_rice_tofu": -1}
    }
  }
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
  "rules": ["R05", "R02", "R06", "R09"],
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "statuses": ["requires_review", "requires_review", "requires_review"],
      "details": [["user_allergy_status_unknown"], ["food_allergen_unknown"], ["goal_nutrient_unknown"]],
      "null_not_zero": true
    }
  }
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
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "mutations": [
        "fact_0478: object_id food_rice_cooked -> food_missing",
        "fact_0479: amount_g -> 0",
        "thêm Not(contains_allergen(food_milk_whole, allergen_milk))"
      ],
      "validation_errors": [["dangling_reference"], ["non_positive_amount"], ["positive_negative_conflict"]],
      "inference_not_started": true
    }
  }
}
```

## TC11 — Nhu cầu và mục tiêu năng lượng theo tuổi/giới/vận động

```json
{
  "id": "TC11",
  "input": {
    "subcases": [
      {"user_id": "user_minh"},
      {"user_id": "user_lan"},
      {"user_id": "user_an"},
      {"user_id": "user_minh", "override_context": {"sex": "unspecified"}}
    ],
    "ratio_check": {"user_id": "user_an", "menu_id": "menu_milk_free"}
  },
  "expected": {
    "energy_requirement": [2800, 2000, 1800, null],
    "energy_target": [2800, 2000, 1300, null],
    "unit": "kcal/ngày",
    "menu_energy_ratio": 1.0264,
    "tolerance": 0.0001
  },
  "rules": ["R10", "R11", "R06"],
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "energy_requirement": [2800, 2000, 1800, null],
      "energy_target": [2800, 2000, 1300, null],
      "unit": "kcal/ngày",
      "menu_energy_ratio": 1.026385,
      "rows_used": "hàng female 31–35 tuổi, cột sedentary"
    }
  }
}
```

## TC12 — Mục tiêu giảm cân bị chặn khi BMI < 25 hoặc thiếu dữ liệu

```json
{
  "id": "TC12",
  "input": {
    "subcases": [
      {"user_id": "user_tam", "menu_id": "menu_ordinary"},
      {"user_id": "user_an", "menu_id": "menu_ordinary"},
      {"user_id": "user_an", "menu_id": "menu_ordinary", "remove_context": ["weight_kg"]}
    ]
  },
  "expected": {
    "statuses": ["requires_review", "eligible_in_model", "requires_review"],
    "details": [["bmi_below_threshold"], [], ["bmi_unknown"]],
    "bmi_premise_contains": "19.61"
  },
  "rules": ["R12", "R02", "R09"],
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "statuses": ["requires_review", "eligible_in_model", "requires_review"],
      "details": [["bmi_below_threshold"], [], ["bmi_unknown"]],
      "r12_premises": [
        "58 / (172 / 100) ** 2 = 19.61",
        "null / (158 / 100) ** 2 = null",
        "user_an.nutrition_goal=lose_weight",
        "user_tam.nutrition_goal=lose_weight"
      ]
    }
  }
}
```

## TC13 — Giảm cân: Menu gần mục tiêu năng lượng hơn, Dish ít năng lượng hơn

```json
{
  "id": "TC13",
  "input": {
    "user_id": "user_an",
    "menu_ids": ["menu_ordinary", "menu_vegetarian", "menu_vegan", "menu_milk_free", "menu_vegan_peanut_free"],
    "dish_ids": ["dish_rice_chicken", "dish_fruit_plate", "dish_lentil_potato"]
  },
  "expected": {
    "energy_target": 1300,
    "menu_order": ["menu_milk_free", "menu_vegetarian", "menu_vegan", "menu_ordinary", "menu_vegan_peanut_free"],
    "menu_energy_kcal": {
      "menu_milk_free": 1334.3,
      "menu_vegetarian": 1233.55,
      "menu_vegan": 1199.5,
      "menu_ordinary": 1438.7,
      "menu_vegan_peanut_free": 1035.0
    },
    "dish_order": ["dish_fruit_plate", "dish_lentil_potato", "dish_rice_chicken"],
    "tolerance": 0.0001
  },
  "rules": ["R06", "R11", "R13", "R09"],
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "energy_target": 1300,
      "menu_order": ["menu_milk_free", "menu_vegetarian", "menu_vegan", "menu_ordinary", "menu_vegan_peanut_free"],
      "menu_energy_kcal": {
        "menu_ordinary": 1438.7,
        "menu_vegetarian": 1233.55,
        "menu_vegan": 1199.5,
        "menu_milk_free": 1334.3,
        "menu_vegan_peanut_free": 1035.0
      },
      "menu_decided_by": ["R13", "R13", "R13", "R13"],
      "dish_order": ["dish_fruit_plate", "dish_lentil_potato", "dish_rice_chicken"]
    }
  }
}
```

## TC14 — Cân bằng nhóm thực phẩm phân định khi đồng hạng

```json
{
  "id": "TC14",
  "input": {
    "subcases": [
      {"user_id": "user_huy", "menu_ids": ["menu_vegan_peanut_free", "menu_vegetarian"]},
      {"user_id": "user_quang", "menu_ids": ["menu_vegan_peanut_free"]}
    ]
  },
  "expected": {
    "order": ["menu_vegetarian", "menu_vegan_peanut_free"],
    "decided_by": ["R14"],
    "coverage": {"menu_vegetarian": "6/6", "menu_vegan_peanut_free": "5/6"},
    "vegan_coverage": {"menu_vegan_peanut_free": "5/5"},
    "vegan_excluded_groups": ["group_dairy"]
  },
  "rules": ["R08", "R14", "R09"],
  "actual_result": {
    "status": "PASS",
    "run_on": "2026-10-16",
    "command": "python tests/update_case_results.py",
    "observed": {
      "order": ["menu_vegetarian", "menu_vegan_peanut_free"],
      "decided_by": ["R14"],
      "coverage": {"menu_vegan_peanut_free": "5/6", "menu_vegetarian": "6/6"},
      "vegan_coverage": {"menu_vegan_peanut_free": "5/5"},
      "vegan_excluded_groups": ["group_dairy"]
    }
  }
}
```
