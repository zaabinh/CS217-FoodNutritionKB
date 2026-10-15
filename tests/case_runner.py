"""Chạy các ca kiểm thử đặc tả trong tests/test_cases.md trên CSTT thật.

``input`` và ``expected`` được đọc trực tiếp từ các khối JSON trong
test_cases.md; mỗi TC có một hàm chạy. Mỗi ca bắt đầu từ bản sao dữ liệu gốc:
``mutation`` và ``override_goal`` chỉ đổi bản sao trong bộ nhớ, không sửa kb/.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from engine import Engine, KBValidationError  # noqa: E402
from kb_loader import KnowledgeBase, load_raw  # noqa: E402
from validate_kb import errors_only, validate  # noqa: E402

CASES_MD = ROOT / "tests" / "test_cases.md"
BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.S)
_BASE = None


def parse_cases(path: Path = CASES_MD) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    return [json.loads(m.group(1)) for m in BLOCK.finditer(text)]


def base_raw() -> dict:
    global _BASE
    if _BASE is None:
        _BASE = load_raw()
    return copy.deepcopy(_BASE)


def engine_for(raw: dict) -> Engine:
    return Engine(KnowledgeBase(raw))


def set_user_goal(raw: dict, user_id: str, goal: str) -> None:
    for user in raw["facts"]["entities"]["user_profile"]:
        if user["id"] == user_id:
            user["nutrition_goal"] = goal


def find_edge(raw: dict, relation: str, subject_id: str, object_id: str | None = None) -> dict:
    for e in raw["facts"]["edges"]:
        if e["relation"] == relation and e["subject_id"] == subject_id and object_id in (None, e["object_id"]):
            return e
    raise KeyError((relation, subject_id, object_id))


def apply_mutation(raw: dict, mutation: dict) -> str:
    """Áp một thay đổi lên bản sao dữ liệu; trả về mô tả để ghi vào kết quả."""
    op = mutation.get("operation")
    if op is None and "target" in mutation:
        for item in raw["facts"]["entities"]["nutrient_content"]:
            if item["id"] == mutation["target"]:
                item.update(mutation["set"])
                return f"{mutation['target']} <- {mutation['set']}"
        raise KeyError(mutation["target"])
    if op == "replace_ingredient_object":
        edge = find_edge(raw, "uses_ingredient", mutation["dish_id"])
        old, edge["object_id"] = edge["object_id"], mutation["new_food_id"]
        return f"{edge['id']}: object_id {old} -> {mutation['new_food_id']}"
    if op == "set_amount_g":
        edge = find_edge(raw, "uses_ingredient", mutation["dish_id"], mutation["food_id"])
        edge["attributes"]["amount_g"] = mutation["value"]
        return f"{edge['id']}: amount_g -> {mutation['value']}"
    if op == "add_negative_edge":
        raw["facts"]["negative_edges"].append({
            "id": "negative_fact_test", "relation": mutation["relation"], "subject_id": mutation["subject_id"],
            "object_id": mutation["object_id"], "attributes": {}, "_meta": {"source_ids": ["source_synthetic"]}})
        return f"thêm Not({mutation['relation']}({mutation['subject_id']}, {mutation['object_id']}))"
    raise ValueError(f"mutation không hỗ trợ: {mutation}")


def close(a, b, tol) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def check_equal(problems, name, actual, expected):
    if actual != expected:
        problems.append(f"{name}: thực tế {actual!r} ≠ kỳ vọng {expected!r}")


RUNNERS = {}


def runner(case_id):
    def deco(fn):
        RUNNERS[case_id] = fn
        return fn
    return deco


@runner("TC01")
def tc01(case):
    kb = KnowledgeBase(base_raw())
    food = case["input"]["food_id"]
    actual = {"group_id": kb.group_of(food), "protein_per_100g": kb.nutrient_value(food, "nutrient_protein"),
              "unit": kb.nutrient_unit("nutrient_protein")}
    problems = []
    for key, value in case["expected"].items():
        check_equal(problems, key, actual[key], value)
    return actual, problems


@runner("TC02")
def tc02(case):
    raw = base_raw()
    eng = engine_for(raw)
    inp, exp = case["input"], case["expected"]
    res = eng.infer(inp["user_id"])
    allergens = sorted({eng.kb.edge_by_id[p]["object_id"] for o in res.origins(inp["food_id"])
                        for p in o["premises"] if eng.kb.edge_by_id.get(p, {}).get("relation") == "contains_allergen"})
    actual = {"status": res.status(inp["food_id"]), "reasons": res.reasons(inp["food_id"]),
              "allergen_ids": allergens, "rules_fired": res.rules_fired(inp["food_id"])}
    problems = []
    check_equal(problems, "status", actual["status"], exp["status"])
    if exp["reason"] not in actual["reasons"]:
        problems.append(f"thiếu lý do {exp['reason']}")
    if exp["allergen_id"] not in allergens:
        problems.append(f"thiếu tác nhân {exp['allergen_id']}")
    return actual, problems


@runner("TC03")
def tc03(case):
    eng = engine_for(base_raw())
    inp, exp = case["input"], case["expected"]
    res = eng.infer(inp["user_id"])
    actual = {"dish_status": res.status(inp["dish_id"]), "menu_status": res.status(inp["menu_id"]),
              "path": res.path(inp["menu_id"]), "rules_fired": res.rules_fired(inp["menu_id"])}
    problems = []
    for key in ("dish_status", "menu_status", "path"):
        check_equal(problems, key, actual[key], exp[key])
    return actual, problems


@runner("TC04")
def tc04(case):
    eng = engine_for(base_raw())
    inp, exp = case["input"], case["expected"]
    res = eng.infer(inp["user_id"])
    actual = {"status": res.status(inp["dish_id"]), "reasons": res.reasons(inp["dish_id"]),
              "origins": sorted({o["origin"] for o in res.origins(inp["dish_id"])}),
              "rules_fired": res.rules_fired(inp["dish_id"])}
    problems = []
    check_equal(problems, "status", actual["status"], exp["status"])
    if exp["reason"] not in actual["reasons"]:
        problems.append(f"thiếu lý do {exp['reason']}")
    return actual, problems


@runner("TC05")
def tc05(case):
    eng = engine_for(base_raw())
    inp, exp = case["input"], case["expected"]
    uid, dish = inp["user_id"], inp["dish_id"]
    res = eng.infer(uid)
    liked = [f for f in eng.foods_of(dish)
             if (e := eng.kb.edge("prefers_food", uid, f)) and e["attributes"]["preference"] == "like"]
    ranking = eng.rank(res, [dish])
    actual = {"status": res.status(dish), "reason_codes": sorted(res.reasons(dish)), "liked_foods": liked,
              "in_ranking": dish in ranking["order"], "notes": [n["note"] for n in res.notes],
              "rules_fired": res.rules_fired(dish)}
    actual["preference_cannot_restore"] = bool(liked) and actual["status"] == "rejected" and not actual["in_ranking"]
    problems = []
    check_equal(problems, "status", actual["status"], exp["status"])
    check_equal(problems, "reason_codes (tập hợp)", actual["reason_codes"], sorted(exp["reason_codes"]))
    check_equal(problems, "preference_cannot_restore", actual["preference_cannot_restore"],
                exp["preference_cannot_restore"])
    return actual, problems


@runner("TC06")
def tc06(case):
    eng = engine_for(base_raw())
    dish, exp = case["input"]["dish_id"], case["expected"]
    res = eng.infer(eng.kb.items("user_profile")[0]["id"])
    values = res.nutrients[dish]
    actual = {"servings": eng.kb.entity(dish)["servings"], "basis": res.nutrient_basis[dish],
              "nutrients_per_serving": {k: round(v, 6) for k, v in values.items()}}
    problems = []
    check_equal(problems, "servings", actual["servings"], exp["servings"])
    for nid, value in exp["nutrients_per_serving"].items():
        if not close(values.get(nid), value, exp["tolerance"]):
            problems.append(f"{nid}: {values.get(nid)} ≠ {value} ± {exp['tolerance']}")
    return actual, problems


@runner("TC07")
def tc07(case):
    eng = engine_for(base_raw())
    inp, exp = case["input"], case["expected"]
    res = eng.infer(inp["user_id"])
    ranking = eng.rank(res, inp["dish_ids"])
    actual = {"order": ranking["order"], "criteria": ranking["criteria"],
              "protein_g": {d: round(res.nutrients[d]["nutrient_protein"], 6) for d in inp["dish_ids"]},
              "decided_by": [d["rule_id"] for d in ranking["decisions"]]}
    problems = []
    check_equal(problems, "order", actual["order"], exp["order"])
    for d, value in exp["protein_g"].items():
        if not close(actual["protein_g"][d], value, 1e-4):
            problems.append(f"protein {d}: {actual['protein_g'][d]} ≠ {value}")
    return actual, problems


@runner("TC08")
def tc08(case):
    exp = case["expected"]
    keys = {"nutrient_fiber": "fiber_order", "nutrient_calcium": "calcium_order", "preference": "preference_order"}
    actual, problems = {}, []
    for sub in case["input"]["subcases"]:
        raw = base_raw()
        if "override_goal" in sub:
            set_user_goal(raw, sub["user_id"], sub["override_goal"])
        eng = engine_for(raw)
        res = eng.infer(sub["user_id"])
        ranking = eng.rank(res, sub["dish_ids"])
        key = keys[sub["metric"]]
        actual[key] = ranking["order"]
        actual[key + "_decided_by"] = [d["rule_id"] for d in ranking["decisions"]]
        check_equal(problems, key, ranking["order"], exp[key])
        if sub["metric"] == "preference":
            scores = {d: ranking["scores"][d]["R09"]["value"] for d in ranking["order"]}
            actual["preference_scores"] = scores
            check_equal(problems, "preference_scores", scores, exp["preference_scores"])
    return actual, problems


@runner("TC09")
def tc09(case):
    exp = case["expected"]
    statuses, details, problems = [], [], []
    null_not_zero = True
    for sub in case["input"]["subcases"]:
        raw = base_raw()
        if "mutation" in sub:
            apply_mutation(raw, sub["mutation"])
        eng = engine_for(raw)
        res = eng.infer(sub["user_id"])
        item = sub.get("dish_id") or sub.get("food_id")
        statuses.append(res.status(item))
        details.append(res.details(item))
        if "mutation" in sub:
            target = sub["mutation"]["target"]
            nc = eng.kb.entity(target)
            nutrient = eng.kb.objects("measures_nutrient", target)[0]["object_id"]
            total = res.nutrients[item][nutrient]
            null_not_zero = null_not_zero and nc["value"] is None and total is None \
                and target in res.missing[item].get(nutrient, [])
    actual = {"statuses": statuses, "details": details, "null_not_zero": null_not_zero}
    check_equal(problems, "statuses", statuses, exp["statuses"])
    check_equal(problems, "null_not_zero", null_not_zero, exp["null_not_zero"])
    return actual, problems


@runner("TC10")
def tc10(case):
    exp = case["expected"]
    codes, changes, not_started, problems = [], [], [], []
    for mutation, want in zip(case["input"]["mutations_separately"], exp["validation_errors"]):
        raw = base_raw()
        changes.append(apply_mutation(raw, mutation))
        found = sorted({i.code for i in errors_only(validate(raw))})
        codes.append(found)
        if want not in found:
            problems.append(f"{mutation['operation']}: không thấy lỗi {want}, có {found}")
        try:
            Engine(KnowledgeBase(raw))
            not_started.append(False)
        except KBValidationError:
            not_started.append(True)
    actual = {"mutations": changes, "validation_errors": codes, "inference_not_started": all(not_started)}
    check_equal(problems, "inference_not_started", actual["inference_not_started"], exp["inference_not_started"])
    return actual, problems


def run_case(case: dict) -> tuple[dict, list[str]]:
    fn = RUNNERS.get(case["id"])
    if fn is None:
        return {}, [f"chưa có hàm chạy cho {case['id']}"]
    return fn(case)
