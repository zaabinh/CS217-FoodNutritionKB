"""Bộ máy suy diễn tiến (forward chaining) cho CSTT dinh dưỡng.

Engine không chứa tri thức miền: mọi luật được đọc từ ``kb/rules.json`` (trường
``exec``). Engine chỉ hiện thực các loại điều kiện và hành động khai báo trong
``rule_dsl.py``; thêm luật cùng loại không cần sửa mã nguồn.

Thứ tự xử lý đọc từ ``rules.json#evaluation_plan``:
  validate_structure -> hard_constraints + propagation (lặp tới điểm cố định)
  -> aggregation -> eligibility -> ranking (khi truy vấn so sánh ứng viên).
Trong một pha, luật priority lớn được xét trước; cùng priority thì theo mã luật.
Mỗi kết luận lưu một Justification: mã luật, lý do, tiền đề (ID Facts) và
thành phần con (nếu được lan truyền) để giải thích.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass

from kb_loader import TRUE, KnowledgeBase
from rule_dsl import MATCHING_ACTIONS, CompiledExpr, compare, is_var
from validate_kb import errors_only, validate

REJECTED, REVIEW, ELIGIBLE = "rejected", "requires_review", "eligible_in_model"
SEVERITY = {REJECTED: 2, REVIEW: 1, ELIGIBLE: 0}
QUERY_PHASES = {"ranking"}


class KBValidationError(Exception):
    """CSTT có lỗi cấu trúc nên không bắt đầu suy diễn."""

    def __init__(self, issues):
        self.issues = issues
        shown = "; ".join(f"{i.code} @ {i.where}" for i in issues[:5])
        super().__init__(f"CSTT có {len(issues)} lỗi, không chạy suy diễn: {shown}")


@dataclass(frozen=True)
class Justification:
    rule_id: str
    value: str
    reason: str
    detail: str | None = None
    premises: tuple = ()
    via: str | None = None
    relation: str | None = None
    notes: tuple = ()

    def key(self):
        return (self.rule_id, self.value, self.reason, self.detail, self.premises, self.via)


class InferenceResult:
    """Kết luận suy ra cho một người dùng."""

    def __init__(self, kb: KnowledgeBase, user_id: str):
        self.kb = kb
        self.user_id = user_id
        self.justifications: dict[str, list[Justification]] = defaultdict(list)
        self._keys: dict[str, set] = defaultdict(set)
        self.nutrients: dict[str, dict] = {}
        self.missing: dict[str, dict] = {}
        self.nutrient_basis: dict[str, str] = {}
        self.nutrient_inputs: dict[str, list] = {}
        self.user_values: dict[str, dict] = {}
        self.item_values: dict[str, dict] = defaultdict(dict)
        self.firings: list[dict] = []
        self.notes: list[dict] = []

    def add(self, item: str, just: Justification) -> bool:
        key = just.key()
        if key in self._keys[item]:
            return False
        self._keys[item].add(key)
        self.justifications[item].append(just)
        return True

    def status(self, item: str) -> str | None:
        values = [j.value for j in self.justifications.get(item, [])]
        if not values:
            return None
        return max(values, key=lambda v: SEVERITY[v])

    def by_value(self, item: str, value: str | None = None) -> list[Justification]:
        value = value or self.status(item)
        return [j for j in self.justifications.get(item, []) if j.value == value]

    def reasons(self, item: str, value: str | None = None) -> list[str]:
        out = []
        for j in self.by_value(item, value):
            if j.reason not in out:
                out.append(j.reason)
        return out

    def details(self, item: str, value: str | None = None) -> list[str]:
        out = []
        for j in self.by_value(item, value):
            if j.detail and j.detail not in out:
                out.append(j.detail)
        return out

    def origin(self, item: str, just: Justification) -> tuple[list[str], Justification]:
        """Đi theo chuỗi R02 xuống thành phần gốc; trả về (đường dẫn gốc->item, luật gốc)."""
        path = [item]
        seen = {item}
        while just.via is not None and just.via not in seen:
            child = just.via
            path.append(child)
            seen.add(child)
            nxt = next((j for j in self.justifications.get(child, [])
                        if j.value == just.value and j.reason == just.reason and j.detail == just.detail), None)
            if nxt is None:
                break
            just = nxt
        return list(reversed(path)), just

    def path(self, item: str, value: str | None = None) -> list[str]:
        firsts = self.by_value(item, value)
        return self.origin(item, firsts[0])[0] if firsts else [item]

    def origins(self, item: str, value: str | None = None) -> list[dict]:
        """Các luật gốc (không phải lan truyền) dẫn tới trạng thái của item."""
        out, seen = [], set()
        for j in self.by_value(item, value):
            path, root = self.origin(item, j)
            key = (root.rule_id, root.reason, root.detail, path[0])
            if key in seen:
                continue
            seen.add(key)
            out.append({"rule_id": root.rule_id, "reason": root.reason, "detail": root.detail,
                        "origin": path[0], "path": path, "premises": list(root.premises), "notes": list(root.notes)})
        return out

    def rules_fired(self, item: str) -> list[str]:
        ids = set()
        for j in self.justifications.get(item, []):
            ids.add(j.rule_id)
            if j.via:
                ids.update(o["rule_id"] for o in self.origins(item, j.value))
        return sorted(ids)


class Engine:
    def __init__(self, kb: KnowledgeBase, validate_first: bool = True):
        if validate_first:
            errors = errors_only(validate(kb.raw))
            if errors:
                raise KBValidationError(errors)
        self.kb = kb
        self.rules = kb.rules
        self._exprs: dict[str, CompiledExpr] = {}
        known = {r["phase"] for r in self.rules}
        self.plan = []
        for step in kb.evaluation_plan:
            phases = [p for p in re.findall(r"[a-z_]+", step) if p in known]
            if phases:
                self.plan.append((tuple(phases), "fixed point" in step))

    # ----- tiện ích -------------------------------------------------------
    def _rules_in(self, phases) -> list[dict]:
        return sorted((r for r in self.rules if r["phase"] in phases), key=lambda r: (-r["priority"], r["id"]))

    def _action(self, rule) -> str:
        return rule["exec"]["then"]["action"]

    def _compiled(self, text: str) -> CompiledExpr:
        if text not in self._exprs:
            self._exprs[text] = CompiledExpr(text)
        return self._exprs[text]

    @staticmethod
    def _val(term, bindings):
        return bindings.get(term) if is_var(term) else term

    def _resolve_path(self, ref: str, bindings):
        var, _, rest = ref.partition(".")
        entity = bindings.get(var)
        return self.kb.attr(entity, rest) if entity else None

    def children_relations(self) -> list[str]:
        """Quan hệ cha -> con lấy từ luật lan truyền (R02), không mã hóa cứng."""
        rels = []
        for rule in self.rules:
            if self._action(rule) == "propagate_status":
                rels.extend(r for r in rule["exec"]["then"]["via"] if r not in rels)
        return rels

    def foods_of(self, item: str) -> list[str]:
        """Các food (không trùng) cấu thành item; food trả về chính nó."""
        if self.kb.concept_of.get(item) == "food":
            return [item]
        rels = self.children_relations()
        out, stack, seen = [], [item], set()
        while stack:
            current = stack.pop()
            for rel in rels:
                for e in self.kb.objects(rel, current):
                    child = e["object_id"]
                    if child in seen:
                        continue
                    seen.add(child)
                    if self.kb.concept_of.get(child) == "food":
                        out.append(child)
                    else:
                        stack.append(child)
        return sorted(out)

    def goal_specs(self) -> list[tuple[str, dict]]:
        return [(r["id"], r["exec"]["then"]["goals"]) for r in self._rules_in(QUERY_PHASES)
                if self._action(r) == "goal_metric"]

    # ----- khớp điều kiện -------------------------------------------------
    def _match(self, conds, bindings, res):
        if not conds:
            yield bindings, []
            return
        for b2, p in self._eval(conds[0], bindings, res):
            for b3, p2 in self._match(conds[1:], b2, res):
                yield b3, p + p2

    def _eval(self, cond, b, res):
        kb = self.kb
        if "rel" in cond:
            rel, (s_t, o_t) = cond["rel"], cond["args"]
            truth, where = cond.get("truth", TRUE), cond.get("where", {})
            s, o = self._val(s_t, b), self._val(o_t, b)
            if truth == TRUE:
                if s is not None and o is not None:
                    edge = kb.edge(rel, s, o)
                    edges = [edge] if edge else []
                elif s is not None:
                    edges = kb.objects(rel, s)
                elif o is not None:
                    edges = kb.subjects(rel, o)
                else:
                    edges = kb.edges_of(rel)
                for e in edges:
                    if any(e.get("attributes", {}).get(k) != v for k, v in where.items()):
                        continue
                    nb = dict(b)
                    if is_var(s_t):
                        nb[s_t] = e["subject_id"]
                    if is_var(o_t):
                        nb[o_t] = e["object_id"]
                    yield nb, [e["id"]]
            else:
                spec = kb.relations[rel]
                subjects = [s] if s is not None else [x["id"] for x in kb.items(spec["domain"])]
                objects = [o] if o is not None else [x["id"] for x in kb.items(spec["range"])]
                for si in subjects:
                    for oi in objects:
                        value, premise = kb.holds(rel, si, oi)
                        if value == truth:
                            nb = dict(b)
                            if is_var(s_t):
                                nb[s_t] = si
                            if is_var(o_t):
                                nb[o_t] = oi
                            yield nb, [premise]
        elif "each" in cond:
            var, concept = cond["var"], cond["each"]
            if var in b:
                if kb.concept_of.get(b[var]) == concept:
                    yield b, []
            else:
                for item in kb.items(concept):
                    yield {**b, var: item["id"]}, []
        elif "attr" in cond:
            var, _, path = cond["attr"].partition(".")
            entity = b.get(var)
            if entity is None:
                return
            value = kb.attr(entity, path)
            if compare(cond["op"], value, cond.get("value")):
                yield b, [f"{entity}.{path}={'null' if value is None else value}"]
        elif "expr" in cond:
            expr = self._compiled(cond["expr"])
            value = expr.evaluate(lambda ref: self._resolve_path(ref, b))
            if compare(cond["op"], value, cond.get("value")):
                shown = cond["expr"]
                for ref in expr.refs:
                    v = self._resolve_path(ref, b)
                    shown = shown.replace(ref, "null" if v is None else str(v))
                yield b, [f"{shown} = {'null' if value is None else round(value, 2)}"]
        elif "goal_nutrient" in cond:
            u_t, n_t = cond["goal_nutrient"]
            user = b.get(u_t)
            goal = kb.attr(user, "nutrition_goal")
            for rule_id, goals in self.goal_specs():
                if goal in goals:
                    nutrient = goals[goal]["nutrient"]
                    if is_var(n_t) and n_t in b and b[n_t] != nutrient:
                        continue
                    yield {**b, n_t: nutrient}, [f"{user}.nutrition_goal={goal} cần {nutrient} ({rule_id})"]
        elif "nutrient_value" in cond:
            f_t, n_t = cond["nutrient_value"]
            want_known = cond.get("truth", "known") == "known"
            f, n = self._val(f_t, b), self._val(n_t, b)
            foods = [f] if f is not None else [x["id"] for x in kb.items("food")]
            nutrients = [n] if n is not None else [x["id"] for x in kb.items("nutrient")]
            for fid in foods:
                for nid in nutrients:
                    record = kb.nutrient_content(fid, nid)
                    known = record is not None and record.get("status") == "known"
                    if known == want_known:
                        nb = dict(b)
                        if is_var(f_t):
                            nb[f_t] = fid
                        if is_var(n_t):
                            nb[n_t] = nid
                        yield nb, [record["id"] if record else f"thiếu bản ghi {fid}/{nid}"]
        elif "status" in cond:
            x_t = cond["status"]
            x = self._val(x_t, b)
            items = [x] if x is not None else list(res.justifications)
            for item in items:
                if res.status(item) == cond["value"]:
                    yield ({**b, x_t: item} if is_var(x_t) else b), [f"status({item})={cond['value']}"]

    # ----- hành động --------------------------------------------------------
    def _fire(self, rule, res) -> bool:
        action = self._action(rule)
        if action in MATCHING_ACTIONS:
            return self._fire_matching(rule, res)
        handler = {
            "propagate_status": self._fire_propagate,
            "aggregate_nutrients": self._fire_aggregate,
            "lookup_table": self._fire_lookup,
            "energy_target": self._fire_energy_target,
            "set_eligible": self._fire_eligible,
        }.get(action)
        return handler(rule, res) if handler else False

    def _log(self, res, rule, item, summary):
        res.firings.append({"rule_id": rule["id"], "phase": rule["phase"], "item": item, "summary": summary})

    def _fire_matching(self, rule, res) -> bool:
        ex, then = rule["exec"], rule["exec"]["then"]
        changed = False
        for branch in ex.get("when_any") or [{}]:
            conds = ex.get("when", []) + branch.get("when", [])
            target_term = branch.get("target", then.get("target"))
            for b, premises in self._match(conds, {"?u": res.user_id}, res):
                target = self._val(target_term, b)
                notes = ()
                note_if = then.get("note_if")
                if note_if:
                    hit = next(self._match(note_if["when"], b, res), None)
                    if hit is not None:
                        notes = (f"{note_if['note']} [{', '.join(hit[1])}]",)
                just = Justification(rule["id"], then["value"], then["reason"], branch.get("detail"),
                                     tuple(premises), notes=notes)
                if res.add(target, just):
                    changed = True
                    self._log(res, rule, target, f"{then['value']}: {then['reason']}"
                              + (f"/{branch['detail']}" if branch.get("detail") else ""))
                    if notes:
                        res.notes.append({"rule_id": rule["id"], "item": target, "note": notes[0]})
        return changed

    def _fire_propagate(self, rule, res) -> bool:
        then = rule["exec"]["then"]
        order = then.get("order", [REJECTED, REVIEW])
        changed = False
        for rel in then["via"]:
            for e in self.kb.edges_of(rel):
                parent, child = e["subject_id"], e["object_id"]
                for j in list(res.justifications.get(child, [])):
                    if j.value not in order:
                        continue
                    nj = Justification(rule["id"], j.value, j.reason, j.detail, (e["id"],), via=child, relation=rel)
                    if res.add(parent, nj):
                        changed = True
                        self._log(res, rule, parent, f"{j.value} từ {child} ({rel})")
        return changed

    def _fire_aggregate(self, rule, res) -> bool:
        if res.nutrients:
            return False
        kb = self.kb
        nutrients = [n["id"] for n in kb.items("nutrient")]
        basis = kb.comparison_basis
        for food in kb.items("food"):
            fid = food["id"]
            res.nutrients[fid] = {n: kb.nutrient_value(fid, n) for n in nutrients}
            res.missing[fid] = {}
            for n in nutrients:
                if res.nutrients[fid][n] is None:
                    record = kb.nutrient_content(fid, n)
                    res.missing[fid][n] = [record["id"] if record else f"{fid}/{n}"]
            res.nutrient_basis[fid] = basis.get("food", "per_100g")
        for step in rule["exec"]["then"]["steps"]:
            for parent in kb.items(step["concept"]):
                pid = parent["id"]
                totals = {n: 0.0 for n in nutrients}
                missing = defaultdict(list)
                inputs = []
                for e in kb.objects(step["via"], pid):
                    child = e["object_id"]
                    weight = e.get("attributes", {}).get(step["weight_attr"], 1) if step.get("weight_attr") else 1
                    inputs.append({"child": child, "weight": weight, "edge": e["id"]})
                    for n in nutrients:
                        value = res.nutrients.get(child, {}).get(n)
                        if value is None:
                            for m in res.missing.get(child, {}).get(n, [child]):
                                if m not in missing[n]:
                                    missing[n].append(m)
                            totals[n] = None
                            continue
                        if totals[n] is None:
                            continue
                        factor = weight
                        if step.get("per_basis_g"):
                            factor = weight / kb.nutrient_content(child, n)["basis_g"]
                        totals[n] += factor * value
                if step.get("divide_by_attr"):
                    divisor = parent[step["divide_by_attr"]]
                    totals = {n: (t / divisor if t is not None else None) for n, t in totals.items()}
                res.nutrients[pid] = totals
                res.missing[pid] = dict(missing)
                res.nutrient_basis[pid] = step.get("basis", basis.get(step["concept"]))
                res.nutrient_inputs[pid] = inputs
        self._log(res, rule, None, "tổng hợp dinh dưỡng cho dish/meal/menu")
        return True

    def _fire_lookup(self, rule, res) -> bool:
        then = rule["exec"]["then"]
        if then["output"] in res.user_values:
            return False
        b = {"?u": res.user_id}
        values, premises = {}, []
        for name, ref in then["inputs"].items():
            values[name] = self._resolve_path(ref, b)
            premises.append(f"{res.user_id}.{ref.partition('.')[2]}={values[name]}")
        row_found = None
        for row in then["rows"]:
            r = dict(zip(then["columns"], row))
            ok = True
            for m in then["match"]:
                v = values.get(m["input"])
                if "column" in m:
                    ok = ok and v == r[m["column"]]
                else:
                    low, high = r[m["min_column"]], r[m["max_column"]]
                    ok = ok and v is not None and (low is None or v >= low) and (high is None or v <= high)
            if ok:
                row_found = r
                break
        column = then["select"]["map"].get(values.get(then["select"]["input"]))
        value = row_found[column] if row_found and column else None
        if value is None:
            detail = "không có hàng phù hợp trong bảng (ví dụ giới tính chưa xác định)"
        else:
            span = "+" if row_found.get("age_max") is None else f"–{row_found['age_max']}"
            detail = f"hàng {row_found.get('sex')} {row_found.get('age_min')}{span} tuổi, cột {column}"
        res.user_values[then["output"]] = {"value": value, "unit": then.get("unit"), "rule_id": rule["id"],
                                           "premises": premises, "detail": detail}
        self._log(res, rule, res.user_id, f"{then['output']}={value}")
        return True

    def _fire_energy_target(self, rule, res) -> bool:
        then = rule["exec"]["then"]
        if then["output"] in res.user_values:
            return False
        kb, uid = self.kb, res.user_id
        requirement = res.user_values.get(then["requirement"], {}).get("value")
        goal = kb.attr(uid, "nutrition_goal")
        sex = kb.attr(uid, "context.sex")
        adjust = then.get("adjustments", {}).get(goal)
        if requirement is None:
            value, detail = None, f"chưa có {then['requirement']}"
        elif adjust:
            floor = adjust.get("floor_kcal_by_sex", {}).get(sex)
            if floor is None:
                value, detail = None, f"không có sàn năng lượng cho giới tính {sex!r}"
            else:
                value = max(requirement - adjust["deficit_kcal"], floor)
                detail = f"max({requirement} − {adjust['deficit_kcal']}, sàn {floor}) cho mục tiêu {goal}"
        else:
            value, detail = requirement, f"bằng {then['requirement']} (mục tiêu {goal})"
        res.user_values[then["output"]] = {"value": value, "unit": then.get("unit"), "rule_id": rule["id"],
                                           "premises": [f"{uid}.nutrition_goal={goal}", f"{uid}.context.sex={sex}",
                                                        f"{then['requirement']}={requirement}"],
                                           "detail": detail}
        ratio = then.get("ratio")
        if ratio:
            for item in kb.items(ratio["concept"]):
                energy = res.nutrients.get(item["id"], {}).get(ratio["nutrient"])
                res.item_values[item["id"]][ratio["output"]] = (
                    energy / value if energy is not None and value else None)
        self._log(res, rule, uid, f"{then['output']}={value}")
        return True

    def _fire_eligible(self, rule, res) -> bool:
        then = rule["exec"]["then"]
        changed = False
        for concept in then["concepts"]:
            for item in self.kb.items(concept):
                if res.status(item["id"]) is None:
                    just = Justification(rule["id"], then["value"], then["reason"],
                                         premises=("không có rejected/requires_review sau điểm cố định",))
                    changed |= res.add(item["id"], just)
        self._log(res, rule, None, "xác nhận eligible_in_model cho ứng viên còn lại")
        return changed

    # ----- suy diễn -------------------------------------------------------
    def infer(self, user_id: str) -> InferenceResult:
        if self.kb.concept_of.get(user_id) != "user_profile":
            raise KeyError(f"{user_id!r} không phải user_profile trong CSTT")
        res = InferenceResult(self.kb, user_id)
        for phases, fixed_point in self.plan:
            if QUERY_PHASES.intersection(phases):
                continue
            rules = self._rules_in(phases)
            for _ in range(100):
                changed = False
                for rule in rules:
                    changed |= self._fire(rule, res)
                if not fixed_point or not changed:
                    break
        return res

    # ----- xếp hạng --------------------------------------------------------
    def _scorer(self, rule, res, concept):
        kb, uid = self.kb, res.user_id
        then = rule["exec"]["then"]
        action = then["action"]
        if action == "goal_metric":
            spec = then["goals"].get(kb.attr(uid, "nutrition_goal"))
            if spec is None:
                return None
            nutrient, mode = spec["nutrient"], spec.get("by_concept", {}).get(concept)
            unit = kb.nutrient_unit(nutrient)

            def score(item):
                value = res.nutrients.get(item, {}).get(nutrient)
                if value is None:
                    return -math.inf, {"value": None, "nutrient": nutrient}
                if mode:
                    target = res.user_values.get(mode["target"], {}).get("value")
                    if target is None:
                        return -math.inf, {"value": value, "target": None, "nutrient": nutrient}
                    return -abs(value - target), {"value": round(value, 3), "unit": unit, "nutrient": nutrient,
                                                  "target": target, "distance": round(abs(value - target), 3)}
                s = value if spec["direction"] == "desc" else -value
                return s, {"value": round(value, 3), "unit": unit, "nutrient": nutrient,
                           "direction": spec["direction"], "basis": res.nutrient_basis.get(item)}
            return score
        if action == "preference_score":
            weights, default = then["weights"], then.get("default", 0)

            def score(item):
                total, likes, dislikes = 0, [], []
                for food in self.foods_of(item):
                    edge = kb.edge(then["relation"], uid, food)
                    pref = edge["attributes"].get(then["attribute"]) if edge else None
                    total += weights.get(pref, default)
                    if pref == "like":
                        likes.append(food)
                    elif pref == "dislike":
                        dislikes.append(food)
                return total, {"value": total, "likes": likes, "dislikes": dislikes}
            return score
        if action == "group_coverage":
            if concept not in then["applies_to"]:
                return None
            excluded = []
            for spec in then.get("exclude_groups", []):
                for conds in spec.get("when_any", []):
                    hit = next(self._match(conds, {"?u": uid}, res), None)
                    if hit is not None:
                        excluded.append({"group": spec["group"], "because": hit[1]})
                        break
            required = [g for g in then["groups"] if g not in {x["group"] for x in excluded}]
            membership = then["membership_relation"]

            def score(item):
                present = {e["object_id"] for f in self.foods_of(item) for e in kb.objects(membership, f)}
                covered = [g for g in required if g in present]
                return len(covered), {"value": len(covered), "required": len(required), "covered": covered,
                                      "missing": [g for g in required if g not in present], "excluded": excluded}
            return score
        return None

    def rank(self, res: InferenceResult, item_ids=None, concept: str | None = None) -> dict:
        """Xếp hạng ứng viên eligible cùng concept theo các luật pha ranking."""
        kb = self.kb
        if item_ids is None:
            item_ids = [x["id"] for x in kb.items(concept)]
        concepts = {kb.concept_of.get(i) for i in item_ids}
        if len(concepts) != 1 or None in concepts:
            raise ValueError(f"chỉ so sánh ứng viên cùng một concept đã khai báo, nhận {sorted(map(str, concepts))}")
        concept = concepts.pop()
        eligible = [i for i in item_ids if res.status(i) == ELIGIBLE]
        criteria = []
        for rule in self._rules_in(QUERY_PHASES):
            scorer = self._scorer(rule, res, concept)
            if scorer is not None:
                criteria.append((rule["id"], scorer))
        scores = {i: [(rid, *scorer(i)) for rid, scorer in criteria] for i in eligible}
        order = sorted(eligible, key=lambda i: (tuple(-s for _, s, _ in scores[i]), i))
        decisions = []
        for a, b in zip(order, order[1:]):
            decided = next(((rid, sa, sb) for (rid, sa, da), (_, sb, db) in zip(scores[a], scores[b]) if sa != sb), None)
            if decided:
                rid = decided[0]
                da = next(d for r, _, d in scores[a] if r == rid)
                db = next(d for r, _, d in scores[b] if r == rid)
                decisions.append({"higher": a, "lower": b, "rule_id": rid, "higher_info": da, "lower_info": db})
            else:
                decisions.append({"higher": a, "lower": b, "rule_id": self._tie_break_rule(),
                                  "higher_info": {}, "lower_info": {}, "tie": True})
        return {
            "user_id": res.user_id,
            "concept": concept,
            "basis": kb.comparison_basis.get(concept),
            "criteria": [rid for rid, _ in criteria],
            "order": order,
            "scores": {i: {rid: info for rid, _, info in scores[i]} for i in eligible},
            "decisions": decisions,
            "excluded": [{"id": i, "status": res.status(i), "reasons": res.reasons(i)}
                         for i in item_ids if i not in eligible],
        }

    def _tie_break_rule(self) -> str:
        for rule in self.rules:
            if self._action(rule) == "set_eligible":
                return rule["id"]
        return "id_asc"

    def recommend(self, user_id: str, concept: str = "menu") -> tuple[InferenceResult, dict]:
        res = self.infer(user_id)
        return res, self.rank(res, concept=concept)


def load_engine(kb_dir=None) -> Engine:
    kb = KnowledgeBase.from_dir(kb_dir) if kb_dir else KnowledgeBase.from_dir()
    return Engine(kb)
