"""Kiểm thử validate_kb: mỗi loại lỗi được phát hiện trên bản sao dữ liệu bị làm hỏng."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from case_runner import ROOT, base_raw, find_edge

from kb_loader import KBLoadError, load_raw
from validate_kb import errors_only, validate


def codes(raw):
    return {i.code for i in errors_only(validate(raw))}


def entity(raw, concept, eid):
    return next(x for x in raw["facts"]["entities"][concept] if x["id"] == eid)


class CleanKB(unittest.TestCase):
    def test_current_kb_has_no_errors_or_warnings(self):
        issues = validate(base_raw())
        self.assertEqual(issues, [], [str(i) for i in issues])


class ValidatorDetects(unittest.TestCase):
    def assertDetects(self, raw, code):
        found = codes(raw)
        self.assertIn(code, found, f"không phát hiện {code}; có {found}")

    def test_duplicate_entity_id(self):
        raw = base_raw()
        raw["facts"]["entities"]["food"].append(dict(entity(raw, "food", "food_rice_cooked")))
        self.assertDetects(raw, "duplicate_id")

    def test_duplicate_rule_id(self):
        raw = base_raw()
        raw["rules"]["rules"].append(dict(raw["rules"]["rules"][0]))
        self.assertDetects(raw, "duplicate_id")

    def test_dangling_reference(self):
        raw = base_raw()
        find_edge(raw, "contains_dish", "meal_ordinary_lunch")["object_id"] = "dish_khong_ton_tai"
        self.assertDetects(raw, "dangling_reference")

    def test_domain_mismatch(self):
        raw = base_raw()
        find_edge(raw, "belongs_to_group", "food_rice_cooked")["subject_id"] = "dish_rice_chicken"
        self.assertDetects(raw, "domain_mismatch")

    def test_cardinality_food_with_two_groups(self):
        raw = base_raw()
        edge = dict(find_edge(raw, "belongs_to_group", "food_rice_cooked"), id="fact_x", object_id="group_fruits")
        raw["facts"]["edges"].append(edge)
        self.assertDetects(raw, "cardinality_violation")

    def test_cardinality_user_without_diet(self):
        raw = base_raw()
        raw["facts"]["edges"].remove(find_edge(raw, "follows_diet", "user_minh"))
        self.assertDetects(raw, "cardinality_violation")

    def test_menu_needs_one_meal_of_each_type(self):
        raw = base_raw()
        find_edge(raw, "contains_meal", "menu_ordinary", "meal_ordinary_lunch")["object_id"] = "meal_vegan_breakfast"
        self.assertDetects(raw, "menu_meal_types")

    def test_enum_and_type_and_missing_attribute(self):
        raw = base_raw()
        entity(raw, "food", "food_rice_cooked")["origin"] = "alien"
        entity(raw, "dish", "dish_rice_chicken")["servings"] = "1"
        del entity(raw, "food", "food_apple_raw")["name"]
        found = codes(raw)
        self.assertTrue({"enum_violation", "type_mismatch", "missing_attribute"} <= found, found)

    def test_user_age_below_minimum(self):
        raw = base_raw()
        entity(raw, "user_profile", "user_minh")["context"]["age"] = 15
        self.assertDetects(raw, "value_out_of_bounds")

    def test_unknown_nutrient_must_stay_null(self):
        raw = base_raw()
        entity(raw, "nutrient_content", "nc_shrimp_cooked_fiber")["value"] = 0
        self.assertDetects(raw, "nutrient_status_mismatch")

    def test_known_nutrient_needs_value(self):
        raw = base_raw()
        entity(raw, "nutrient_content", "nc_rice_cooked_protein")["value"] = None
        self.assertDetects(raw, "nutrient_status_mismatch")

    def test_unknown_source(self):
        raw = base_raw()
        find_edge(raw, "allergic_to", "user_minh")["_meta"]["source_ids"] = ["source_bia"]
        self.assertDetects(raw, "unknown_source")

    def test_positive_negative_conflict(self):
        raw = base_raw()
        raw["facts"]["negative_edges"].append({"id": "neg_x", "relation": "contains_allergen",
                                               "subject_id": "food_tofu_firm", "object_id": "allergen_soy",
                                               "attributes": {}, "_meta": {"source_ids": ["source_design"]}})
        self.assertDetects(raw, "positive_negative_conflict")

    def test_negative_edge_not_allowed_for_relation(self):
        raw = base_raw()
        raw["facts"]["negative_edges"].append({"id": "neg_y", "relation": "allergic_to", "subject_id": "user_minh",
                                               "object_id": "allergen_egg", "attributes": {},
                                               "_meta": {"source_ids": ["source_synthetic"]}})
        self.assertDetects(raw, "negative_not_allowed")

    def test_non_positive_servings(self):
        raw = base_raw()
        find_edge(raw, "contains_dish", "meal_ordinary_lunch")["attributes"]["servings"] = 0
        self.assertDetects(raw, "non_positive_amount")

    def test_duplicate_edge(self):
        raw = base_raw()
        raw["facts"]["edges"].append(dict(find_edge(raw, "allergic_to", "user_minh"), id="fact_dup"))
        self.assertDetects(raw, "duplicate_edge")

    def test_preference_enum(self):
        raw = base_raw()
        find_edge(raw, "prefers_food", "user_minh")["attributes"]["preference"] = "love"
        self.assertDetects(raw, "enum_violation")

    def test_rule_with_unknown_action(self):
        raw = base_raw()
        raw["rules"]["rules"][0]["exec"]["then"]["action"] = "delete_food"
        self.assertDetects(raw, "rule_invalid")

    def test_rule_with_unknown_relation_or_constant(self):
        raw = base_raw()
        when = raw["rules"]["rules"][0]["exec"]["when"]
        when[0]["rel"] = "is_allergic"
        when[1]["args"][1] = "allergen_gluten"
        self.assertDetects(raw, "rule_invalid")

    def test_rule_in_wrong_phase(self):
        raw = base_raw()
        raw["rules"]["rules"][0]["phase"] = "ranking"
        self.assertDetects(raw, "rule_invalid")

    def test_rule_without_exec(self):
        raw = base_raw()
        del raw["rules"]["rules"][0]["exec"]
        self.assertDetects(raw, "rule_invalid")


class BrokenFiles(unittest.TestCase):
    def test_invalid_json_file_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("concepts.json", "relations.json", "facts.json", "rules.json"):
                (Path(tmp) / name).write_text((ROOT / "kb" / name).read_text(encoding="utf-8"), encoding="utf-8")
            (Path(tmp) / "rules.json").write_text('{"rules": [', encoding="utf-8")
            with self.assertRaises(KBLoadError):
                load_raw(tmp)
            proc = subprocess.run([sys.executable, str(ROOT / "src" / "validate_kb.py"), "--kb", tmp, "--json"],
                                  capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(json.loads(proc.stdout)[0]["code"], "json_error")

    def test_cli_on_real_kb_succeeds(self):
        proc = subprocess.run([sys.executable, str(ROOT / "src" / "validate_kb.py"), "--json"],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
