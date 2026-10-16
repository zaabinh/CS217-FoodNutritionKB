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



class GeneralizedNutrientGoal(unittest.TestCase):
    """R07 dùng chung ánh xạ mục tiêu/chất; không còn nhánh luật riêng cho chất xơ/canxi."""

    def test_three_nutrient_goals_are_decided_by_r07(self):
        cases = [
            ("prefer_protein", "user_minh", "dish_rice_chicken", "dish_chickpea_salad", "nutrient_protein"),
            ("prefer_fiber", "user_lan", "dish_lentil_potato", "dish_chickpea_salad", "nutrient_fiber"),
            ("prefer_calcium", "user_minh", "dish_rice_tofu", "dish_chickpea_salad", "nutrient_calcium"),
        ]
        for goal, uid, higher, lower, nutrient in cases:
            with self.subTest(goal=goal):
                raw = base_raw()
                set_user_goal(raw, uid, goal)
                self.assertNotIn("R15", {r["id"] for r in raw["rules"]["rules"]})
                eng = engine_for(raw)
                ranking = eng.rank(eng.infer(uid), [lower, higher])
                self.assertEqual(ranking["order"], [higher, lower])
                self.assertEqual(ranking["criteria"], ["R07", "R08"])
                self.assertEqual(ranking["decisions"][0]["rule_id"], "R07")
                self.assertEqual(ranking["scores"][higher]["R07"]["nutrient"], nutrient)

    def test_each_goal_blocks_unknown_target_nutrient(self):
        for goal, suffix in [("prefer_protein", "protein"), ("prefer_fiber", "fiber"), ("prefer_calcium", "calcium")]:
            with self.subTest(goal=goal):
                raw = base_raw()
                set_user_goal(raw, "user_minh", goal)
                nc = next(n for n in raw["facts"]["entities"]["nutrient_content"]
                          if n["id"] == "nc_rice_cooked_" + suffix)
                nc.update(status="unknown", value=None, source_record_id=None)
                eng = engine_for(raw)
                res = eng.infer("user_minh")
                self.assertEqual(res.status("dish_rice_chicken"), REVIEW)
                self.assertIn("goal_nutrient_unknown", res.details("dish_rice_chicken"))
                self.assertNotIn("dish_rice_chicken", eng.rank(res, concept="dish")["order"])

    def test_new_nutrient_goal_only_needs_json_configuration(self):
        raw = base_raw()
        profile = next(c for c in raw["concepts"]["concepts"] if c["id"] == "user_profile")
        goal = next(a for a in profile["attributes"] if a["name"] == "nutrition_goal")
        goal["enum"].append("prefer_lipid")
        r07 = next(r for r in raw["rules"]["rules"] if r["id"] == "R07")
        r07["exec"]["then"]["goals"]["prefer_lipid"] = {"nutrient": "nutrient_lipid", "direction": "desc"}
        set_user_goal(raw, "user_minh", "prefer_lipid")
        eng = engine_for(raw)
        ranking = eng.rank(eng.infer("user_minh"), ["food_rice_cooked", "food_olive_oil"])
        self.assertEqual(ranking["order"], ["food_olive_oil", "food_rice_cooked"])
        self.assertEqual(ranking["decisions"][0]["rule_id"], "R07")
        self.assertEqual(ranking["scores"]["food_olive_oil"]["R07"]["nutrient"], "nutrient_lipid")


class EnergyAndWeightGoal(unittest.TestCase):
    """R10–R14: năng lượng, giảm cân an toàn, cân bằng nhóm."""

    def _values(self, **context):
        raw = base_raw()
        user(raw, "user_minh")["context"].update(context)
        return engine_for(raw).infer("user_minh").user_values

    def test_energy_table_boundaries(self):
        self.assertEqual(self._values(age=20, activity="low")["energy_requirement"]["value"], 2600)
        self.assertEqual(self._values(age=21, activity="low")["energy_requirement"]["value"], 2400)
        self.assertEqual(self._values(age=90, activity="high")["energy_requirement"]["value"], 2400)
        self.assertEqual(self._values(age=90, sex="female", activity="low")["energy_requirement"]["value"], 1600)

    def test_every_adult_age_sex_activity_has_a_value(self):
        raw = base_raw()
        rule = next(r for r in raw["rules"]["rules"] if r["id"] == "R10")
        rows = rule["exec"]["then"]["rows"]
        for sex in ("male", "female"):
            for age in range(18, 101):
                hits = [r for r in rows if r[0] == sex and r[1] <= age and (r[2] is None or age <= r[2])]
                self.assertEqual(len(hits), 1, f"{sex} {age} tuổi khớp {len(hits)} hàng")

    def test_unspecified_sex_gives_null_not_a_guess(self):
        values = self._values(sex="unspecified")
        self.assertIsNone(values["energy_requirement"]["value"])
        self.assertIsNone(values["energy_target"]["value"])

    def test_weight_loss_target_never_below_floor(self):
        raw = base_raw()
        user(raw, "user_an")["context"].update(age=80)        # EER 1600 -> 1600 - 500 < sàn 1200
        self.assertEqual(engine_for(raw).infer("user_an").user_values["energy_target"]["value"], 1200)

    def test_weight_loss_blocked_without_bmi_or_below_threshold(self):
        eng = engine_for(base_raw())
        tam = eng.infer("user_tam")
        for concept in CANDIDATES:
            for item in eng.kb.items(concept):
                self.assertEqual(tam.status(item["id"]), REVIEW, item["id"])
        raw = base_raw()
        user(raw, "user_an")["context"]["sex"] = "unspecified"
        res = engine_for(raw).infer("user_an")
        self.assertIn("sex_unspecified", res.details("menu_ordinary"))

    def test_other_goals_do_not_need_weight(self):
        res = engine_for(base_raw()).infer("user_minh")   # không có weight_kg/height_cm
        self.assertEqual(res.status("menu_milk_free"), ELIGIBLE)

    def test_allergy_still_wins_over_weight_loss_goal(self):
        raw = base_raw()
        add_edge(raw, "fact_t_an_allergy", "allergic_to", "user_an", "allergen_milk")
        eng = engine_for(raw)
        res = eng.infer("user_an")
        self.assertEqual(res.status("menu_ordinary"), REJECTED)
        self.assertNotIn("menu_ordinary", eng.rank(res, concept="menu")["order"])

    def test_dairy_not_required_for_milk_allergy(self):
        eng = engine_for(base_raw())
        ranking = eng.rank(eng.infer("user_minh"), concept="menu")
        for scores in ranking["scores"].values():
            self.assertEqual(scores["R14"]["required"], 5)
            self.assertEqual(scores["R14"]["excluded"][0]["group"], "group_dairy")

    def test_group_coverage_only_for_menus(self):
        eng = engine_for(base_raw())
        ranking = eng.rank(eng.infer("user_huy"), concept="dish")
        self.assertNotIn("R14", ranking["criteria"])


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
