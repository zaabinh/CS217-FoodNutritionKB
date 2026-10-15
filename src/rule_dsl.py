"""Đặc tả ngôn ngữ luật thực thi (trường ``exec`` trong kb/rules.json).

Một luật có dạng::

    "exec": {
      "when":     [điều kiện, ...],              # AND, tùy chọn
      "when_any": [{"when": [...], "detail": "...", "target": "?x"}, ...],  # OR, tùy chọn
      "then":     {"action": "<tên hành động>", ...tham số}
    }

Điều kiện (mỗi điều kiện là một object có đúng một khóa loại):

- ``{"rel": R, "args": [s, o], "truth": "true|false|unknown", "where": {...}}``
- ``{"each": concept, "var": "?x"}``
- ``{"attr": "?x.path", "op": OP, "value": V}``
- ``{"expr": "biểu thức số học trên ?x.path", "op": OP, "value": V}``
- ``{"goal_nutrient": ["?u", "?n"]}``
- ``{"nutrient_value": ["?f", "?n"], "truth": "known|unknown"}``
- ``{"status": "?x", "value": "rejected|requires_review|eligible_in_model"}``

Biến bắt đầu bằng ``?``; ``?u`` luôn được gán sẵn là người dùng đang xét.
Thêm luật mới chỉ cần JSON nếu dùng các điều kiện/hành động có ở đây;
hành động mới cần bổ sung bộ xử lý trong ``engine.py``.
"""
from __future__ import annotations

import ast
import operator
import re

STATUS_VALUES = ("rejected", "requires_review", "eligible_in_model")
TRUTH_VALUES = ("true", "false", "unknown")
CONDITION_KINDS = ("rel", "each", "attr", "expr", "goal_nutrient", "nutrient_value", "status")
OPS = ("eq", "ne", "in", "not_in", "lt", "le", "gt", "ge", "missing", "present")
RULE_KINDS = ("hard", "soft", "calculation")

# action -> (pha hợp lệ, tham số bắt buộc trong "then")
ACTIONS = {
    "set_status": ({"hard_constraints"}, ("value", "reason")),
    "set_status_unless_rejected": ({"hard_constraints"}, ("value", "reason")),
    "propagate_status": ({"propagation"}, ("via",)),
    "aggregate_nutrients": ({"aggregation"}, ("steps",)),
    "lookup_table": ({"aggregation"}, ("output", "inputs", "columns", "rows", "match", "select")),
    "energy_target": ({"aggregation"}, ("requirement", "output")),
    "set_eligible": ({"eligibility"}, ("value", "reason", "concepts")),
    "goal_metric": ({"ranking"}, ("goals",)),
    "preference_score": ({"ranking"}, ("relation", "attribute", "weights")),
    "group_coverage": ({"ranking"}, ("applies_to", "membership_relation", "groups")),
}
MATCHING_ACTIONS = ("set_status", "set_status_unless_rejected")


def is_var(term) -> bool:
    return isinstance(term, str) and term.startswith("?")


# ---------------------------------------------------------------------------
# Biểu thức số học an toàn: + - * / **, max, min, abs, round, hằng số và
# tham chiếu thuộc tính dạng ?x.a.b. Không dùng eval().
# ---------------------------------------------------------------------------
_REF = re.compile(r"\?[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")
_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.Pow: operator.pow}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"max": max, "min": min, "abs": abs, "round": round}


class ExprError(ValueError):
    pass


class CompiledExpr:
    def __init__(self, text: str):
        self.text = text
        self.refs: list[str] = []

        def repl(match):
            self.refs.append(match.group(0))
            return f"__r{len(self.refs) - 1}"

        try:
            self.tree = ast.parse(_REF.sub(repl, text), mode="eval")
        except SyntaxError as exc:
            raise ExprError(f"biểu thức sai cú pháp: {text!r}") from exc
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Expression, ast.Load, ast.BinOp, ast.UnaryOp, ast.Call)):
                continue
            if isinstance(node, tuple(_BINOPS)) or isinstance(node, tuple(_UNARY)):
                continue
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                continue
            if isinstance(node, ast.Name) and (node.id in _FUNCS or node.id.startswith("__r")):
                continue
            raise ExprError(f"phần tử không được phép trong biểu thức {text!r}: {type(node).__name__}")

    def evaluate(self, resolve):
        """``resolve(ref)`` trả về giá trị của ``?x.path``; thiếu bất kỳ giá trị nào -> None."""
        values = [resolve(ref) for ref in self.refs]
        if any(v is None or isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
            return None
        return self._eval(self.tree.body, values)

    def _eval(self, node, values):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return values[int(node.id[3:])]
        if isinstance(node, ast.BinOp):
            return _BINOPS[type(node.op)](self._eval(node.left, values), self._eval(node.right, values))
        if isinstance(node, ast.UnaryOp):
            return _UNARY[type(node.op)](self._eval(node.operand, values))
        if isinstance(node, ast.Call):
            return _FUNCS[node.func.id](*(self._eval(a, values) for a in node.args))
        raise ExprError(f"không tính được {ast.dump(node)}")


def compare(op: str, left, right) -> bool:
    if op == "missing":
        return left is None
    if op == "present":
        return left is not None
    if op == "eq":
        return left == right
    if op == "ne":
        return left != right
    if op == "in":
        return left in right
    if op == "not_in":
        return left not in right
    if left is None:
        return False
    return {"lt": left < right, "le": left <= right, "gt": left > right, "ge": left >= right}[op]


# ---------------------------------------------------------------------------
# Kiểm tra cấu trúc exec (dùng bởi validate_kb.py)
# ---------------------------------------------------------------------------
class _Ctx:
    def __init__(self, raw: dict):
        self.concepts = {c["id"]: c for c in raw["concepts"].get("concepts", [])}
        self.relations = {r["name"]: r for r in raw["relations"].get("relations", [])}
        self.entities = {}
        for concept_id, items in raw["facts"].get("entities", {}).items():
            for item in items:
                self.entities[item.get("id")] = concept_id
        goal_attr = next((a for a in self.concepts.get("user_profile", {}).get("attributes", [])
                          if a.get("name") == "nutrition_goal"), {})
        self.goals = set(goal_attr.get("enum", []))


def _check_term(term, ctx, problems, where):
    if is_var(term):
        return
    if not isinstance(term, str) or term not in ctx.entities:
        problems.append(f"{where}: hằng {term!r} không phải ID thực thể đã khai báo")


def _check_condition(cond, ctx, problems, where, bound):
    if not isinstance(cond, dict):
        problems.append(f"{where}: điều kiện phải là object")
        return
    kinds = [k for k in CONDITION_KINDS if k in cond]
    if len(kinds) != 1:
        problems.append(f"{where}: điều kiện cần đúng một khóa trong {CONDITION_KINDS}, có {list(cond)}")
        return
    kind = kinds[0]
    if kind == "rel":
        rel = ctx.relations.get(cond["rel"])
        if rel is None:
            problems.append(f"{where}: quan hệ {cond['rel']!r} không có trong relations.json")
            return
        args = cond.get("args")
        if not isinstance(args, list) or len(args) != 2:
            problems.append(f"{where}: 'args' của rel phải có 2 phần tử")
            return
        for t in args:
            _check_term(t, ctx, problems, where)
            if is_var(t):
                bound.add(t)
        if cond.get("truth", "true") not in TRUTH_VALUES:
            problems.append(f"{where}: truth phải thuộc {TRUTH_VALUES}")
        for key in cond.get("where", {}):
            if key not in rel.get("edge_attributes", {}):
                problems.append(f"{where}: thuộc tính cạnh {key!r} không khai báo cho {cond['rel']}")
    elif kind == "each":
        if cond["each"] not in ctx.concepts:
            problems.append(f"{where}: concept {cond['each']!r} không tồn tại")
        if not is_var(cond.get("var")):
            problems.append(f"{where}: 'var' của each phải là biến ?x")
        else:
            bound.add(cond["var"])
    elif kind == "attr":
        path = cond["attr"]
        if not (isinstance(path, str) and is_var(path.split(".")[0]) and "." in path):
            problems.append(f"{where}: attr phải có dạng ?x.thuoc_tinh")
        _check_op(cond, problems, where)
    elif kind == "expr":
        try:
            CompiledExpr(cond["expr"])
        except ExprError as exc:
            problems.append(f"{where}: {exc}")
        _check_op(cond, problems, where)
    elif kind == "goal_nutrient":
        args = cond["goal_nutrient"]
        if not (isinstance(args, list) and len(args) == 2 and all(is_var(a) for a in args)):
            problems.append(f"{where}: goal_nutrient cần 2 biến")
        else:
            bound.update(args)
    elif kind == "nutrient_value":
        args = cond["nutrient_value"]
        if not (isinstance(args, list) and len(args) == 2):
            problems.append(f"{where}: nutrient_value cần 2 tham số")
        else:
            for t in args:
                _check_term(t, ctx, problems, where)
                if is_var(t):
                    bound.add(t)
        if cond.get("truth", "known") not in ("known", "unknown"):
            problems.append(f"{where}: truth của nutrient_value phải là known/unknown")
    elif kind == "status":
        if cond.get("value") not in STATUS_VALUES:
            problems.append(f"{where}: value của status phải thuộc {STATUS_VALUES}")
        if is_var(cond["status"]):
            bound.add(cond["status"])


def _check_op(cond, problems, where):
    op = cond.get("op")
    if op not in OPS:
        problems.append(f"{where}: op {op!r} không thuộc {OPS}")
    elif op not in ("missing", "present") and "value" not in cond:
        problems.append(f"{where}: op {op!r} cần 'value'")


def _check_conditions(conds, ctx, problems, where, bound):
    if not isinstance(conds, list):
        problems.append(f"{where}: phải là danh sách điều kiện")
        return
    for i, cond in enumerate(conds):
        _check_condition(cond, ctx, problems, f"{where}[{i}]", bound)


def check_exec(rule: dict, raw: dict, phases: set[str]) -> list[str]:
    """Trả về danh sách mô tả lỗi của trường exec trong một luật."""
    ctx = _Ctx(raw)
    problems: list[str] = []
    ex = rule.get("exec")
    if not isinstance(ex, dict):
        return ["thiếu trường 'exec' nên bộ máy suy diễn không thực thi được luật"]
    then = ex.get("then")
    if not isinstance(then, dict) or then.get("action") not in ACTIONS:
        return [f"exec.then.action phải thuộc {sorted(ACTIONS)}"]
    action = then["action"]
    allowed_phases, required = ACTIONS[action]
    if rule.get("phase") not in allowed_phases:
        problems.append(f"hành động {action} chỉ dùng trong pha {sorted(allowed_phases)}, luật ở pha {rule.get('phase')!r}")
    if rule.get("phase") not in phases:
        problems.append(f"pha {rule.get('phase')!r} không có trong evaluation_plan")
    for key in required:
        if key not in then:
            problems.append(f"exec.then thiếu tham số {key!r} cho {action}")

    bound = {"?u"}
    _check_conditions(ex.get("when", []), ctx, problems, "exec.when", bound)
    for i, branch in enumerate(ex.get("when_any", [])):
        branch_bound = set(bound)
        _check_conditions(branch.get("when", []), ctx, problems, f"exec.when_any[{i}].when", branch_bound)
        target = branch.get("target", then.get("target"))
        if action in MATCHING_ACTIONS and (not is_var(target) or target not in branch_bound):
            problems.append(f"exec.when_any[{i}]: đích {target!r} chưa được gán bởi điều kiện")
    if action in MATCHING_ACTIONS:
        if then.get("value") not in STATUS_VALUES:
            problems.append(f"exec.then.value phải thuộc {STATUS_VALUES}")
        if not ex.get("when_any"):
            target = then.get("target")
            if not is_var(target) or target not in bound:
                problems.append(f"exec.then.target {target!r} chưa được gán bởi điều kiện")
        note = then.get("note_if")
        if note:
            _check_conditions(note.get("when", []), ctx, problems, "exec.then.note_if.when", set(bound))

    if action == "propagate_status":
        for rel in then.get("via", []):
            if rel not in ctx.relations:
                problems.append(f"via: quan hệ {rel!r} không tồn tại")
    elif action == "aggregate_nutrients":
        for i, step in enumerate(then.get("steps", [])):
            rel = ctx.relations.get(step.get("via"))
            if step.get("concept") not in ctx.concepts:
                problems.append(f"steps[{i}]: concept {step.get('concept')!r} không tồn tại")
            if rel is None:
                problems.append(f"steps[{i}]: quan hệ {step.get('via')!r} không tồn tại")
            elif step.get("weight_attr") and step["weight_attr"] not in rel.get("edge_attributes", {}):
                problems.append(f"steps[{i}]: {step['weight_attr']!r} không phải thuộc tính cạnh của {step['via']}")
    elif action == "goal_metric":
        for goal, spec in then.get("goals", {}).items():
            if goal not in ctx.goals:
                problems.append(f"goals: mục tiêu {goal!r} không có trong enum nutrition_goal")
            if ctx.entities.get(spec.get("nutrient")) != "nutrient":
                problems.append(f"goals.{goal}: nutrient {spec.get('nutrient')!r} không tồn tại")
            if spec.get("direction") not in ("desc", "asc"):
                problems.append(f"goals.{goal}: direction phải là desc/asc")
            for concept, mode in spec.get("by_concept", {}).items():
                if concept not in ctx.concepts or mode.get("mode") != "closest_to":
                    problems.append(f"goals.{goal}.by_concept.{concept}: chỉ hỗ trợ mode closest_to cho concept có thật")
    elif action == "preference_score":
        rel = ctx.relations.get(then.get("relation"))
        if rel is None or then.get("attribute") not in rel.get("edge_attributes", {}):
            problems.append("preference_score: relation/attribute không khớp relations.json")
    elif action == "group_coverage":
        if then.get("membership_relation") not in ctx.relations:
            problems.append("group_coverage: membership_relation không tồn tại")
        for g in then.get("groups", []):
            if ctx.entities.get(g) != "food_group":
                problems.append(f"group_coverage: nhóm {g!r} không tồn tại")
        for i, ex_spec in enumerate(then.get("exclude_groups", [])):
            if ex_spec.get("group") not in then.get("groups", []):
                problems.append(f"exclude_groups[{i}]: nhóm không nằm trong groups")
            for j, conds in enumerate(ex_spec.get("when_any", [])):
                _check_conditions(conds, ctx, problems, f"exclude_groups[{i}].when_any[{j}]", {"?u"})
    elif action == "lookup_table":
        columns = then.get("columns", [])
        for i, row in enumerate(then.get("rows", [])):
            if not isinstance(row, list) or len(row) != len(columns):
                problems.append(f"rows[{i}]: cần {len(columns)} cột")
        for m in then.get("match", []):
            if m.get("input") not in then.get("inputs", {}):
                problems.append(f"match: input {m.get('input')!r} không khai báo")
        select = then.get("select", {})
        for col in select.get("map", {}).values():
            if col not in columns:
                problems.append(f"select.map: cột {col!r} không có trong columns")
    elif action == "set_eligible":
        for c in then.get("concepts", []):
            if c not in ctx.concepts:
                problems.append(f"set_eligible: concept {c!r} không tồn tại")
    return problems
