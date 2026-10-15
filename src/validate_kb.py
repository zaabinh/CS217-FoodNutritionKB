"""Kiểm tra tính hợp lệ của cơ sở tri thức trong kb/.

Kiểm tra theo chính đặc tả trong CSTT:
- Concepts/Attributes (concepts.json): thuộc tính bắt buộc, kiểu, enum, const, minimum.
- Relations (relations.json): domain/range, bội số, thuộc tính cạnh, phủ định hợp lệ.
- Facts (facts.json): trùng ID, tham chiếu không tồn tại, khẳng định–phủ định mâu thuẫn,
  nguồn được dẫn, bản ghi hàm lượng, mỗi Menu đủ một bữa sáng/trưa/tối.
- Rules (rules.json): pha, loại, concept/relation/nguồn tham chiếu, cấu trúc exec.

Chạy:  python src/validate_kb.py [--kb THU_MUC] [--json] [--strict]
Mã thoát 0 khi không có lỗi (cảnh báo không làm thất bại, trừ khi --strict).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kb_loader import KB_DIR, KBLoadError, load_raw  # noqa: E402
from rule_dsl import RULE_KINDS, check_exec  # noqa: E402

ERROR, WARNING = "error", "warning"
REQUIRED_SECTIONS = {
    "concepts": ["concepts"],
    "relations": ["relations"],
    "facts": ["entities", "edges", "negative_edges", "sources"],
    "rules": ["rules", "evaluation_plan", "status_order"],
}
ATWATER_TOLERANCE = (0.7, 1.4)  # chỉ cảnh báo, không chặn


@dataclass
class Issue:
    severity: str
    code: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper():7}] {self.code:28} {self.where}: {self.message}"


class _Collector:
    def __init__(self):
        self.issues: list[Issue] = []

    def error(self, code, where, message):
        self.issues.append(Issue(ERROR, code, where, message))

    def warn(self, code, where, message):
        self.issues.append(Issue(WARNING, code, where, message))


def _parse_cardinality(text: str) -> tuple[int, int | None]:
    low, high = text.split("..")
    return int(low), (None if high == "*" else int(high))


def _type_ok(value, expected) -> bool:
    if isinstance(expected, list):
        return any(_type_ok(value, t) for t in expected)
    if expected == "null":
        return value is None
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "enum":
        return isinstance(value, str)
    return True


def _check_value(col, where, name, value, spec):
    """Kiểm tra một giá trị theo đặc tả thuộc tính (dùng cho cả thuộc tính lồng trong object)."""
    expected = spec.get("type")
    if expected is not None and not _type_ok(value, expected):
        col.error("type_mismatch", where, f"{name}={value!r} không đúng kiểu {expected}")
        return
    if value is None:
        return
    allowed = spec.get("enum") or spec.get("values")
    if allowed is not None and value not in allowed:
        col.error("enum_violation", where, f"{name}={value!r} không thuộc {allowed}")
    if "const" in spec and value != spec["const"]:
        col.error("const_violation", where, f"{name}={value!r} phải bằng {spec['const']!r}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in spec and value < spec["minimum"]:
            col.error("value_out_of_bounds", where, f"{name}={value} < {spec['minimum']}")
        if "exclusive_minimum" in spec and value <= spec["exclusive_minimum"]:
            col.error("value_out_of_bounds", where, f"{name}={value} phải > {spec['exclusive_minimum']}")
    if expected == "object" and "properties" in spec:
        for field in spec.get("required_fields", []):
            if field not in value:
                col.error("missing_attribute", where, f"{name}.{field} bắt buộc nhưng không có")
        for field, sub in value.items():
            if field not in spec["properties"]:
                col.warn("unexpected_attribute", where, f"{name}.{field} không khai báo trong concepts.json")
            else:
                _check_value(col, where, f"{name}.{field}", sub, spec["properties"][field])


def _check_sections(raw, col) -> bool:
    ok = True
    for key, sections in REQUIRED_SECTIONS.items():
        for section in sections:
            if section not in raw.get(key, {}):
                col.error("missing_section", f"{key}.json", f"thiếu mục '{section}'")
                ok = False
    return ok


def _check_source_ids(col, where, meta, sources):
    for sid in (meta or {}).get("source_ids", []):
        if sid not in sources:
            col.error("unknown_source", where, f"nguồn {sid!r} không có trong facts.sources")


def validate(raw: dict) -> list[Issue]:
    """Kiểm tra dữ liệu thô đã nạp; trả về danh sách lỗi và cảnh báo."""
    col = _Collector()
    if not _check_sections(raw, col):
        return col.issues

    concepts = {}
    for c in raw["concepts"]["concepts"]:
        if c["id"] in concepts:
            col.error("duplicate_id", f"concepts:{c['id']}", "concept khai báo hai lần")
        concepts[c["id"]] = c
    relations = {}
    rel_ids = Counter(r.get("id") for r in raw["relations"]["relations"])
    for rid, n in rel_ids.items():
        if n > 1:
            col.error("duplicate_id", f"relations:{rid}", f"ID quan hệ xuất hiện {n} lần")
    for r in raw["relations"]["relations"]:
        if r["name"] in relations:
            col.error("duplicate_id", f"relations:{r['name']}", "tên quan hệ khai báo hai lần")
        relations[r["name"]] = r
        for end in ("domain", "range"):
            if r.get(end) not in concepts:
                col.error("unknown_concept", f"relations:{r['name']}", f"{end}={r.get(end)!r} không phải concept")
        domain_attrs = {a["name"] for a in concepts.get(r.get("domain"), {}).get("attributes", [])}
        for policy in r.get("negative_rules", []):
            attr = policy.get("status_attribute")
            if attr is not None and attr not in domain_attrs:
                col.error("unknown_attribute", f"relations:{r['name']}",
                          f"status_attribute={attr!r} không phải thuộc tính của {r.get('domain')}")

    facts = raw["facts"]
    sources = {}
    for s in facts["sources"]:
        if s["id"] in sources:
            col.error("duplicate_id", f"sources:{s['id']}", "nguồn khai báo hai lần")
        sources[s["id"]] = s

    # ----- thực thể ------------------------------------------------------
    entity_concept: dict[str, str] = {}
    entities: dict[str, dict] = {}
    for concept_id, items in facts["entities"].items():
        spec = concepts.get(concept_id)
        if spec is None:
            col.error("unknown_concept", f"facts.entities.{concept_id}", "không có concept tương ứng")
            continue
        attr_specs = {a["name"]: a for a in spec["attributes"]}
        for item in items:
            eid = item.get("id")
            where = f"{concept_id}:{eid}"
            if eid in entity_concept:
                col.error("duplicate_id", where, f"ID đã dùng cho {entity_concept[eid]}")
            entity_concept[eid] = concept_id
            entities[eid] = item
            for name, a in attr_specs.items():
                if name not in item:
                    if a.get("required"):
                        col.error("missing_attribute", where, f"thiếu thuộc tính bắt buộc {name}")
                    continue
                _check_value(col, where, name, item[name], a)
            for name in item:
                if name not in attr_specs and name != "_meta":
                    col.warn("unexpected_attribute", where, f"thuộc tính {name} không khai báo")
            _check_source_ids(col, where, item.get("_meta"), sources)

    # ----- cạnh ----------------------------------------------------------
    edge_ids = Counter()
    seen = defaultdict(list)
    out_count = defaultdict(lambda: defaultdict(int))
    in_count = defaultdict(lambda: defaultdict(int))
    positive = set()
    for kind in ("edges", "negative_edges"):
        for e in facts[kind]:
            eid = e.get("id")
            where = f"{kind}:{eid}"
            edge_ids[eid] += 1
            if eid in entity_concept:
                col.error("duplicate_id", where, "ID cạnh trùng ID thực thể")
            rel = relations.get(e.get("relation"))
            if rel is None:
                col.error("unknown_relation", where, f"quan hệ {e.get('relation')!r} không có trong relations.json")
                continue
            s, o = e.get("subject_id"), e.get("object_id")
            bad_ref = False
            for end, ref, want in (("subject_id", s, rel["domain"]), ("object_id", o, rel["range"])):
                if ref not in entity_concept:
                    col.error("dangling_reference", where, f"{end}={ref!r} không tồn tại")
                    bad_ref = True
                elif entity_concept[ref] != want:
                    code = "domain_mismatch" if end == "subject_id" else "range_mismatch"
                    col.error(code, where, f"{end}={ref!r} là {entity_concept[ref]}, cần {want}")
            _check_source_ids(col, where, e.get("_meta"), sources)
            triple = (e["relation"], s, o)
            if kind == "negative_edges":
                if not rel.get("negative_rules"):
                    col.error("negative_not_allowed", where, f"{e['relation']} không khai báo negative_rules")
                if triple in positive:
                    col.error("positive_negative_conflict", where,
                              f"{e['relation']}({s}, {o}) vừa khẳng định vừa phủ định")
                continue
            seen[triple].append(eid)
            positive.add(triple)
            if not bad_ref:
                out_count[e["relation"]][s] += 1
                in_count[e["relation"]][o] += 1
            attrs = e.get("attributes", {})
            for name, spec in rel.get("edge_attributes", {}).items():
                if name not in attrs:
                    col.error("edge_attribute_missing", where, f"thiếu thuộc tính cạnh {name}")
                    continue
                value = attrs[name]
                if spec.get("exclusive_minimum") == 0 and isinstance(value, (int, float)) and value <= 0:
                    col.error("non_positive_amount", where, f"{name}={value} phải > 0")
                    continue
                _check_value(col, where, name, value, spec)
            for name in attrs:
                if name not in rel.get("edge_attributes", {}):
                    col.warn("unexpected_attribute", where, f"thuộc tính cạnh {name} không khai báo")
    for eid, n in edge_ids.items():
        if n > 1:
            col.error("duplicate_id", f"edges:{eid}", f"ID cạnh xuất hiện {n} lần")
    for (rel_name, s, o), ids in seen.items():
        if len(ids) > 1:
            col.error("duplicate_edge", f"edges:{','.join(ids)}", f"{rel_name}({s}, {o}) lặp {len(ids)} lần")

    # ----- bội số --------------------------------------------------------
    by_concept = defaultdict(list)
    for eid, concept_id in entity_concept.items():
        by_concept[concept_id].append(eid)
    for name, rel in relations.items():
        card = rel.get("cardinality", {})
        for key, end, counts in (("objects_per_subject", rel["domain"], out_count[name]),
                                 ("subjects_per_object", rel["range"], in_count[name])):
            if key not in card:
                continue
            low, high = _parse_cardinality(card[key])
            for eid in by_concept.get(end, []):
                n = counts.get(eid, 0)
                if n < low or (high is not None and n > high):
                    col.error("cardinality_violation", f"{rel['id']}:{eid}",
                              f"{name}: {n} cạnh, cần {card[key]} ({key})")

    # ----- ràng buộc riêng của Facts -------------------------------------
    owner = {e["object_id"]: e["subject_id"] for e in facts["edges"] if e.get("relation") == "has_nutrient_content"}
    measured = {e["subject_id"]: e["object_id"] for e in facts["edges"] if e.get("relation") == "measures_nutrient"}
    pairs = defaultdict(list)
    for nc in facts["entities"].get("nutrient_content", []):
        where = f"nutrient_content:{nc['id']}"
        if nc.get("status") == "known" and (nc.get("value") is None or not nc.get("source_record_id")):
            col.error("nutrient_status_mismatch", where, "status=known cần value không âm và source_record_id")
        if nc.get("status") == "unknown" and nc.get("value") is not None:
            col.error("nutrient_status_mismatch", where, "status=unknown phải giữ value=null (không thay bằng 0)")
        if nc["id"] in owner and nc["id"] in measured:
            pairs[(owner[nc["id"]], measured[nc["id"]])].append(nc["id"])
    for (food, nutrient), ids in pairs.items():
        if len(ids) > 1:
            col.error("duplicate_nutrient_content", f"{food}/{nutrient}", f"nhiều bản ghi: {ids}")

    meal_type = {m["id"]: m.get("meal_type") for m in facts["entities"].get("meal", [])}
    menu_meals = defaultdict(list)
    for e in facts["edges"]:
        if e.get("relation") == "contains_meal":
            menu_meals[e["subject_id"]].append(meal_type.get(e["object_id"]))
    for menu in facts["entities"].get("menu", []):
        types = sorted(t for t in menu_meals.get(menu["id"], []) if t)
        if types != ["breakfast", "dinner", "lunch"]:
            col.error("menu_meal_types", f"menu:{menu['id']}", f"cần đúng một breakfast/lunch/dinner, có {types}")

    # Kiểm tra hợp lý (chỉ cảnh báo): năng lượng so với 4P + 9L + 4C.
    nutrient_values = defaultdict(dict)
    for nc_id, food in owner.items():
        nc = entities.get(nc_id)
        if nc and nc_id in measured:
            nutrient_values[food][measured[nc_id]] = nc.get("value")
    for food, v in nutrient_values.items():
        parts = [v.get(k) for k in ("nutrient_energy", "nutrient_protein", "nutrient_lipid", "nutrient_carbohydrate")]
        if None in parts or not parts[0]:
            continue
        ratio = (4 * parts[1] + 9 * parts[2] + 4 * parts[3]) / parts[0]
        if not ATWATER_TOLERANCE[0] <= ratio <= ATWATER_TOLERANCE[1]:
            col.warn("atwater_mismatch", f"food:{food}",
                     f"4P+9L+4C / năng lượng = {ratio:.2f}, ngoài {ATWATER_TOLERANCE}; cần kiểm chứng số liệu")

    # ----- luật ----------------------------------------------------------
    rules_doc = raw["rules"]
    phases = set()
    for step in rules_doc["evaluation_plan"]:
        phases.update(re.findall(r"[a-z_]+", step))
    rule_ids = Counter(r.get("id") for r in rules_doc["rules"])
    for rid, n in rule_ids.items():
        if n > 1:
            col.error("duplicate_id", f"rules:{rid}", f"mã luật xuất hiện {n} lần")
    for rule in rules_doc["rules"]:
        where = f"rules:{rule.get('id')}"
        if rule.get("kind") not in RULE_KINDS:
            col.error("rule_invalid", where, f"kind={rule.get('kind')!r} không thuộc {RULE_KINDS}")
        if not isinstance(rule.get("priority"), int):
            col.error("rule_invalid", where, "priority phải là số nguyên")
        for cid in rule.get("concept_ids", []):
            if cid not in concepts:
                col.error("unknown_concept", where, f"concept_ids có {cid!r} không tồn tại")
        for rname in rule.get("relation_names", []):
            if rname not in relations:
                col.error("unknown_relation", where, f"relation_names có {rname!r} không tồn tại")
        for sid in rule.get("source_ids", []):
            if sid not in sources:
                col.error("unknown_source", where, f"nguồn {sid!r} không có trong facts.sources")
        for problem in check_exec(rule, raw, phases):
            col.error("rule_invalid", where, problem)
    for c in concepts.values():
        for rid in c.get("related_rule_ids", []):
            if rid not in rule_ids:
                col.error("unknown_rule", f"concepts:{c['id']}", f"related_rule_ids có {rid!r} không tồn tại")
    return col.issues


def errors_only(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.severity == ERROR]


def summary(raw: dict) -> dict:
    facts = raw["facts"]
    return {
        "concepts": len(raw["concepts"]["concepts"]),
        "relations": len(raw["relations"]["relations"]),
        "rules": len(raw["rules"]["rules"]),
        "entities": {k: len(v) for k, v in facts["entities"].items()},
        "edges": len(facts["edges"]),
        "negative_edges": len(facts["negative_edges"]),
        "sources": len(facts["sources"]),
    }


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Kiểm tra tính hợp lệ của CSTT dinh dưỡng.")
    parser.add_argument("--kb", default=str(KB_DIR), help="thư mục chứa 4 tệp JSON (mặc định: kb/)")
    parser.add_argument("--json", action="store_true", help="in kết quả dạng JSON")
    parser.add_argument("--strict", action="store_true", help="coi cảnh báo là lỗi")
    args = parser.parse_args(argv)

    try:
        raw = load_raw(args.kb)
    except KBLoadError as exc:
        issue = Issue(ERROR, "json_error", args.kb, str(exc))
        print(json.dumps([asdict(issue)], ensure_ascii=False, indent=2) if args.json else str(issue))
        return 1
    issues = validate(raw)
    errors = errors_only(issues)
    warnings = [i for i in issues if i.severity == WARNING]
    failed = bool(errors) or (args.strict and bool(warnings))

    if args.json:
        print(json.dumps({"valid": not failed, "summary": summary(raw), "issues": [asdict(i) for i in issues]},
                         ensure_ascii=False, indent=2))
        return 1 if failed else 0

    s = summary(raw)
    print(f"CSTT: {Path(args.kb).resolve()}")
    print(f"  {s['concepts']} concepts, {s['relations']} relations, {s['rules']} rules, {s['sources']} nguồn")
    print("  thực thể: " + ", ".join(f"{k}={v}" for k, v in s["entities"].items()))
    print(f"  {s['edges']} cạnh khẳng định, {s['negative_edges']} cạnh phủ định")
    for issue in issues:
        print(issue)
    print(f"Kết quả: {len(errors)} lỗi, {len(warnings)} cảnh báo -> {'KHÔNG HỢP LỆ' if failed else 'HỢP LỆ'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
