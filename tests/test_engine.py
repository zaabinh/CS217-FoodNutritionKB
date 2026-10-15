"""Kiểm thử bộ máy suy diễn: luật chính và các trường hợp biên.

Trọng tâm an toàn: thực phẩm chứa tác nhân dị ứng của người dùng, cùng mọi
món/bữa/thực đơn chứa nó, LUÔN bị loại, bất kể sở thích hay mục tiêu.
"""
import unittest

from case_runner import base_raw, engine_for, find_edge, set_user_goal

from engine import ELIGIBLE, KBValidationError, REJECTED, REVIEW, Engine
from kb_loader import KnowledgeBase

CANDIDATES = ("food", "dish", "meal", "menu")


def user(raw, uid):
    return next(u for u in raw["facts"]["entities"]["user_profile"] if u["id"] == uid)


def add_edge(raw, eid, relation, s, o, attributes=None):
    raw["facts"]["edges"].append({"id": eid, "relation": relation, "subject_id": s, "object_id": o,
                                  "attributes": attributes or {}, "_meta": {"source_ids": ["source_synthetic"]}})


class AllergyAlwaysExcluded(unittest.TestCase):
    def _assert_allergens_excluded(self, eng, uid):
        res = eng.infer(uid)
        kb = eng.kb
        allergens = [e["object_id"] for e in kb.objects("allergic_to", uid)]
        foods = {e["subject_id"] for a in allergens for e in kb.subjects("contains_allergen", a)}
        for concept in CANDIDATES:
            for item in kb.items(concept):
                if foods & set(eng.foods_of(item["id"])):
                    self.assertEqual(res.status(item["id"]), REJECTED, f"{uid}: {item['id']} chứa dị nguyên")
                    self.assertIn("R01", {o["rule_id"] for o in res.origins(item["id"])})
                    self.assertNotIn(item["id"], eng.rank(res, concept=concept)["order"])
        return foods

    def test_every_declared_allergy_in_kb(self):
        eng = engine_for(base_raw())
        checked = set()
        for u in eng.kb.items("user_profile"):
            checked |= self._assert_allergens_excluded(eng, u["id"])
        self.assertTrue(checked, "CSTT mẫu phải có ít nhất một dị ứng để kiểm tra")

    def test_each_allergen_even_when_liked_and_goal_favours_it(self):
        kb = engine_for(base_raw()).kb
        for allergen in kb.items("allergen"):
            raw = base_raw()
            if not kb.edge("allergic_to", "user_huy", allergen["id"]):
                add_edge(raw, "fact_t_allergy", "allergic_to", "user_huy", allergen["id"])
            set_user_goal(raw, "user_huy", "prefer_protein")
            for i, e in enumerate(kb.subjects("contains_allergen", allergen["id"])):
                existing = next((x for x in raw["facts"]["edges"] if x["relation"] == "prefers_food"
                                 and x["subject_id"] == "user_huy" and x["object_id"] == e["subject_id"]), None)
                if existing:
                    existing["attributes"]["preference"] = "like"
                else:
                    add_edge(raw, f"fact_t_like_{i}", "prefers_food", "user_huy", e["subject_id"], {"preference": "like"})
            with self.subTest(allergen=allergen["id"]):
                foods = self._assert_allergens_excluded(engine_for(raw), "user_huy")
                self.assertTrue(foods, f"không có thực phẩm nào chứa {allergen['id']}")

    def test_unknown_allergy_status_blocks_every_candidate(self):
        eng = engine_for(base_raw())
        res = eng.infer("user_vy")
        for concept in CANDIDATES:
            for item in eng.kb.items(concept):
                self.assertNotEqual(res.status(item["id"]), ELIGIBLE, item["id"])


class MissingDataAndNegation(unittest.TestCase):
    def test_unknown_allergen_status_matters_only_for_allergic_users(self):
        raw = base_raw()
        eng = engine_for(raw)
        self.assertEqual(eng.infer("user_minh").status("food_whole_wheat_bread"), REVIEW)
        raw = base_raw()
        raw["facts"]["edges"].remove(find_edge(raw, "allergic_to", "user_minh"))
        self.assertEqual(engine_for(raw).infer("user_minh").status("food_whole_wheat_bread"), ELIGIBLE)

    def test_explicit_negative_complete_list_and_unknown_are_distinguished(self):
        eng = engine_for(base_raw())
        quang = eng.infer("user_quang")      # thuần chay: có phủ định tường minh
        self.assertEqual(quang.status("food_cheddar"), REJECTED)
        self.assertIn("negative_fact_0010", quang.origins("food_cheddar")[0]["premises"])
        lan = eng.infer("user_lan")          # lacto-ovo: diet_status=unknown -> chưa biết
        self.assertEqual(lan.status("food_cheddar"), REVIEW)
        self.assertIn("food_diet_unknown", lan.details("food_cheddar"))
        self.assertEqual(lan.status("food_chicken_roasted"), REJECTED)
        huy = eng.infer("user_huy")          # thông thường: có cạnh khẳng định
        self.assertEqual(huy.status("food_cheddar"), ELIGIBLE)

    def test_null_is_never_replaced_by_zero(self):
        eng = engine_for(base_raw())
        res = eng.infer("user_minh")
        for item in ("food_shrimp_cooked", "dish_shrimp_rice", "meal_milk_free_dinner", "menu_milk_free"):
            self.assertIsNone(res.nutrients[item]["nutrient_fiber"], item)
            self.assertEqual(res.missing[item]["nutrient_fiber"], ["nc_shrimp_cooked_fiber"])
        self.assertIsNotNone(res.nutrients["menu_milk_free"]["nutrient_protein"])

    def test_missing_goal_nutrient_requires_review(self):
        raw = base_raw()
        set_user_goal(raw, "user_minh", "prefer_fiber")
        res = engine_for(raw).infer("user_minh")
        self.assertEqual(res.status("dish_shrimp_rice"), REVIEW)
        self.assertIn("goal_nutrient_unknown", res.details("dish_shrimp_rice"))
        self.assertEqual(res.status("dish_rice_chicken"), ELIGIBLE)

    def test_unknown_recipe_requires_review(self):
        raw = base_raw()
        next(d for d in raw["facts"]["entities"]["dish"] if d["id"] == "dish_fruit_plate")["recipe_status"] = "unknown"
        res = engine_for(raw).infer("user_huy")
        self.assertEqual(res.status("dish_fruit_plate"), REVIEW)
        self.assertEqual(res.status("menu_vegan_peanut_free"), REVIEW)

    def test_rejected_wins_over_requires_review(self):
        raw = base_raw()
        user(raw, "user_lan")["allergy_status"] = "unknown"
        res = engine_for(raw).infer("user_lan")
        self.assertEqual(res.status("food_chicken_roasted"), REJECTED)
        self.assertEqual(res.status("food_banana_raw"), REVIEW)
        self.assertEqual(res.status("dish_rice_chicken"), REJECTED)


class ConflictsAndRanking(unittest.TestCase):
    def test_avoid_beats_like_and_conflict_is_recorded(self):
        eng = engine_for(base_raw())
        res = eng.infer("user_quang")
        self.assertEqual(res.status("food_chicken_roasted"), REJECTED)
        self.assertIn("explicit_avoid", res.reasons("food_chicken_roasted"))
        self.assertTrue(any(n["item"] == "food_chicken_roasted" and "avoid_overrides_like" in n["note"]
                            for n in res.notes))

    def test_ranking_only_same_concept(self):
        eng = engine_for(base_raw())
        res = eng.infer("user_minh")
        with self.assertRaises(ValueError):
            eng.rank(res, ["dish_rice_chicken", "menu_vegan"])

    def test_ranking_keeps_excluded_out_with_reasons(self):
        eng = engine_for(base_raw())
        res = eng.infer("user_minh")
        ranking = eng.rank(res, concept="menu")
        excluded = {e["id"]: e for e in ranking["excluded"]}
        self.assertEqual(set(excluded), {"menu_ordinary", "menu_vegetarian"})
        self.assertEqual(excluded["menu_ordinary"]["reasons"], ["allergen_match"])
        self.assertEqual(ranking["order"][0], "menu_milk_free")

    def test_ties_broken_by_id(self):
        eng = engine_for(base_raw())
        res = eng.infer("user_huy")
        ranking = eng.rank(res, ["dish_rice_chicken", "dish_chickpea_salad", "dish_lentil_potato"])
        tied = [d for d in ranking["decisions"] if d.get("tie")]
        self.assertTrue(tied)
        self.assertEqual(ranking["order"][1:], sorted(ranking["order"][1:]))

    def test_food_level_ranking_uses_per_100g(self):
        eng = engine_for(base_raw())
        res = eng.infer("user_minh")
        ranking = eng.rank(res, ["food_rice_cooked", "food_chicken_roasted", "food_lentil_boiled"])
        self.assertEqual(ranking["order"], ["food_chicken_roasted", "food_lentil_boiled", "food_rice_cooked"])
        self.assertEqual(ranking["basis"], "per_100g")


class Extensibility(unittest.TestCase):
    """Thêm luật bằng JSON, không sửa engine."""

    NEW_RULE = {
        "id": "R99", "name": "Thử nghiệm: loại thực phẩm nhóm chất béo", "phase": "hard_constraints",
        "priority": 100, "kind": "hard", "concept_ids": ["food", "food_group"],
        "relation_names": ["belongs_to_group"], "source_ids": ["source_design"],
        "exec": {"when": [{"rel": "belongs_to_group", "args": ["?f", "group_fats_oils"]}],
                 "then": {"action": "set_status", "target": "?f", "value": "rejected", "reason": "test_group"}},
    }

    def test_new_rule_from_json_only(self):
        raw = base_raw()
        raw["rules"]["rules"].append(self.NEW_RULE)
        res = engine_for(raw).infer("user_huy")
        self.assertEqual(res.status("food_olive_oil"), REJECTED)
        self.assertEqual(res.status("dish_rice_chicken"), REJECTED)   # lan truyền qua R02
        self.assertEqual(res.path("dish_rice_chicken"), ["food_olive_oil", "dish_rice_chicken"])
        self.assertEqual(res.status("dish_fruit_plate"), ELIGIBLE)

    def test_rule_using_derived_status_reaches_fixed_point(self):
        raw = base_raw()
        raw["rules"]["rules"].append({
            "id": "R98", "name": "Thử nghiệm: xem xét food cùng nhóm với food bị loại", "phase": "hard_constraints",
            "priority": 200, "kind": "hard", "concept_ids": ["food"], "relation_names": ["belongs_to_group"],
            "source_ids": ["source_design"],
            "exec": {"when": [{"each": "food", "var": "?x"}, {"status": "?x", "value": "rejected"},
                              {"rel": "belongs_to_group", "args": ["?x", "?g"]},
                              {"rel": "belongs_to_group", "args": ["?f", "?g"]}],
                     "then": {"action": "set_status_unless_rejected", "target": "?f",
                              "value": "requires_review", "reason": "test_same_group"}}})
        res = engine_for(raw).infer("user_huy")    # R01 loại đậu phộng (group_protein) ở vòng 1
        self.assertEqual(res.status("food_chicken_roasted"), REVIEW)
        self.assertEqual(res.status("food_peanut_roasted"), REJECTED)
        self.assertEqual(res.status("food_rice_cooked"), ELIGIBLE)

    def test_invalid_rule_blocks_inference(self):
        raw = base_raw()
        bad = dict(self.NEW_RULE, exec={"when": [{"rel": "khong_co", "args": ["?f", "?g"]}],
                                         "then": {"action": "set_status", "target": "?f", "value": "rejected",
                                                  "reason": "x"}})
        raw["rules"]["rules"].append(bad)
        with self.assertRaises(KBValidationError):
            Engine(KnowledgeBase(raw))


if __name__ == "__main__":
    unittest.main()
