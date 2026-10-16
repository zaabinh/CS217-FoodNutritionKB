"""Cơ chế giải thích: diễn đạt kết luận của engine bằng tiếng Việt.

Mỗi giải thích nêu mã luật đã kích hoạt, lý do, các Facts tiền đề (ID trong
kb/facts.json) và đường lan truyền food -> dish -> meal -> menu. Nhãn tiếng Việt
dưới đây chỉ để trình bày; mã lý do chưa có nhãn được in nguyên văn.
"""
from __future__ import annotations

from kb_loader import KnowledgeBase

DISCLAIMER = ("Lưu ý: kết quả chỉ mang tính tham khảo trong phạm vi tri thức đã mô hình hóa, "
              "không thay thế tư vấn của bác sĩ hoặc chuyên gia dinh dưỡng. Hồ sơ người dùng là dữ liệu giả lập.")

STATUS_VI = {
    "rejected": "BỊ LOẠI",
    "requires_review": "CẦN XEM XÉT",
    "eligible_in_model": "ĐỦ ĐIỀU KIỆN trong mô hình",
    None: "CHƯA KẾT LUẬN",
}
REASON_VI = {
    "allergen_match": "chứa tác nhân người dùng dị ứng",
    "diet_mismatch": "không phù hợp chế độ ăn",
    "explicit_avoid": "người dùng khai báo cần tránh",
    "missing_required_data": "thiếu dữ liệu cần thiết",
    "weight_loss_not_supported": "mục tiêu giảm cân cần chuyên gia xem xét",
    "all_required_checks_passed": "vượt qua mọi kiểm tra bắt buộc",
}
DETAIL_VI = {
    "user_allergy_status_unknown": "hồ sơ chưa khai báo đầy đủ dị ứng",
    "user_avoid_status_unknown": "hồ sơ chưa khai báo đầy đủ thực phẩm cần tránh",
    "diet_policy_unknown": "định nghĩa chế độ ăn chưa hoàn chỉnh",
    "food_allergen_unknown": "chưa biết thực phẩm có chứa tác nhân dị ứng của người dùng hay không",
    "food_diet_unknown": "chưa biết thực phẩm có phù hợp chế độ ăn hay không",
    "recipe_unknown": "công thức món chưa đầy đủ",
    "goal_nutrient_unknown": "chưa biết hàm lượng chất cần cho mục tiêu",
    "bmi_unknown": "thiếu cân nặng/chiều cao để tính BMI",
    "bmi_below_threshold": "BMI dưới ngưỡng thừa cân",
    "sex_unspecified": "chưa xác định giới tính để ước tính năng lượng",
}
NOTE_VI = {
    "avoid_overrides_like": "người dùng vừa thích vừa cần tránh; ràng buộc tránh thắng sở thích",
}


def label(code, table) -> str:
    return table.get(code, code) if code else ""


def describe_premise(kb: KnowledgeBase, premise: str) -> str:
    edge = kb.edge_by_id.get(premise)
    if edge:
        attrs = {k: v for k, v in edge.get("attributes", {}).items() if k not in ("unit", "quantity_basis")}
        extra = "; " + ", ".join(f"{k}={v}" for k, v in attrs.items()) if attrs else ""
        return f"{edge['relation']}({edge['subject_id']}, {edge['object_id']}{extra}) [{premise}]"
    negative = kb.negative_by_id.get(premise)
    if negative:
        return f"Not({negative['relation']}({negative['subject_id']}, {negative['object_id']})) [{premise}]"
    entity = kb.entity(premise)
    if entity and kb.concept_of.get(premise) == "nutrient_content":
        value = "null" if entity.get("value") is None else entity["value"]
        return f"{premise}: status={entity.get('status')}, value={value}"
    return premise


def rule_name(kb: KnowledgeBase, rule_id: str) -> str:
    rule = kb.rule_by_id.get(rule_id)
    return rule["name"] if rule else rule_id


def _names(ids: list[str], limit: int = 3) -> str:
    return ", ".join(ids[:limit]) + (f", … (+{len(ids) - limit})" if len(ids) > limit else "")


def short_reasons(res, item: str) -> str:
    """Tóm tắt lý do gốc, gộp theo luật: 'R01 chứa ... (food_milk_whole); R03 ...'."""
    groups: dict[tuple, list[str]] = {}
    for o in res.origins(item):
        key = (o["rule_id"], label(o["detail"], DETAIL_VI) or label(o["reason"], REASON_VI))
        origins = groups.setdefault(key, [])
        if o["origin"] not in origins:
            origins.append(o["origin"])
    return "; ".join(f"{rid} {text} ({_names(origins)})" for (rid, text), origins in groups.items())


def explain_status(res, item: str, limit: int = 8) -> list[str]:
    kb = res.kb
    status = res.status(item)
    lines = [f"{item} — {kb.name(item)} [{kb.concept_of.get(item)}] với {res.user_id}: {STATUS_VI[status]}"]
    if status is None:
        return lines
    # Gộp các lý do gốc có cùng luật, lý do và tiền đề (ví dụ R05 áp cho mọi food).
    groups: dict[tuple, list[dict]] = {}
    for o in res.origins(item):
        key = (o["rule_id"], o["reason"], o["detail"], tuple(o["premises"]), tuple(o["notes"]))
        groups.setdefault(key, []).append(o)
    for (rule_id, reason, detail, premises, notes), members in list(groups.items())[:limit]:
        why = label(reason, REASON_VI) + (f" — {label(detail, DETAIL_VI)}" if detail else "")
        lines.append(f"  • {rule_id} ({rule_name(kb, rule_id)}): {why}")
        for p in premises:
            lines.append(f"      tiền đề: {describe_premise(kb, p)}")
        for note in notes:
            code = note.split(" ")[0]
            lines.append(f"      ghi chú: {label(code, NOTE_VI)} {note[len(code):].strip()}")
        first = members[0]["path"]
        if len(first) > 1:
            lines.append(f"      lan truyền R02: {' -> '.join(first)}")
        if len(members) > 1:
            others = [m["origin"] for m in members[1:]]
            lines.append(f"      cùng lý do tại: {_names(others, 6)}")
    if len(groups) > limit:
        lines.append(f"  … và {len(groups) - limit} nhóm lý do khác (dùng --all để xem hết)")
    lines.append(f"  Luật đã kích hoạt cho {item}: {', '.join(res.rules_fired(item))}")
    return lines


def _fmt(value, digits=1):
    if value is None:
        return "null"
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def explain_nutrients(res, item: str) -> list[str]:
    kb = res.kb
    values = res.nutrients.get(item)
    if values is None:
        return [f"{item}: chưa có kết quả tổng hợp dinh dưỡng"]
    lines = [f"Dinh dưỡng {item} — {kb.name(item)} (cơ sở: {res.nutrient_basis.get(item)}; luật R06)"]
    for nid, value in values.items():
        missing = res.missing.get(item, {}).get(nid)
        tail = f"  (thiếu: {', '.join(missing)}; không thay bằng 0)" if missing else ""
        lines.append(f"  {kb.name(nid):30} {_fmt(value, 2):>9} {kb.nutrient_unit(nid)}{tail}")
    inputs = res.nutrient_inputs.get(item)
    if inputs:
        parts = [f"{i['child']}×{i['weight']}" for i in inputs]
        lines.append(f"  thành phần: {', '.join(parts)}")
    ratio = res.item_values.get(item, {}).get("energy_ratio")
    if ratio is not None:
        lines.append(f"  đáp ứng {ratio * 100:.0f}% mục tiêu năng lượng ước tính của {res.user_id} (R11)")
    return lines


def explain_user_values(res) -> list[str]:
    kb = res.kb
    lines = []
    for name, info in res.user_values.items():
        value = "chưa xác định" if info["value"] is None else f"{info['value']} {info.get('unit') or ''}".strip()
        lines.append(f"  {name} = {value} ({info['rule_id']} {rule_name(kb, info['rule_id'])}; {info['detail']})")
    return lines


def _criterion_text(kb, rule_id, info) -> str:
    if not info:
        return ""
    if "nutrient" in info:
        if info.get("value") is None:
            return f"{kb.name(info['nutrient'])} chưa biết"
        if "target" in info:
            return (f"{kb.name(info['nutrient'])} {_fmt(info['value'])} {info.get('unit', '')}, "
                    f"lệch {_fmt(info['distance'])} so với mục tiêu {info['target']}")
        return f"{kb.name(info['nutrient'])} {_fmt(info['value'], 3)} {info.get('unit', '')}"
    if "covered" in info:
        missing = f", thiếu {', '.join(info['missing'])}" if info["missing"] else ""
        return f"phủ {info['value']}/{info['required']} nhóm{missing}"
    if "likes" in info:
        return f"điểm sở thích {info['value']:+d}"
    return str(info)


def explain_ranking(kb: KnowledgeBase, ranking: dict, res=None, top: int | None = None) -> list[str]:
    criteria = ", ".join(f"{rid} ({rule_name(kb, rid)})" for rid in ranking["criteria"]) or "chỉ theo ID"
    lines = [f"Xếp hạng {ranking['concept']} cho {ranking['user_id']} (cơ sở so sánh: {ranking['basis']})",
             f"  tiêu chí theo thứ tự priority: {criteria}; đồng hạng -> ID tăng dần"]
    order = ranking["order"] if top is None else ranking["order"][:top]
    if not order:
        lines.append("  Không có ứng viên đủ điều kiện trong mô hình.")
    for i, item in enumerate(order, 1):
        infos = ranking["scores"][item]
        keys = "; ".join(f"{rid}: {_criterion_text(kb, rid, info)}" for rid, info in infos.items())
        lines.append(f"  {i}. {item} — {kb.name(item)}")
        if keys:
            lines.append(f"       {keys}")
        if res is not None:
            ratio = res.item_values.get(item, {}).get("energy_ratio")
            if ratio is not None:
                lines.append(f"       năng lượng đáp ứng {ratio * 100:.0f}% mục tiêu ước tính (R11)")
    for d in ranking["decisions"][: (len(order) - 1 if top else None)]:
        if d.get("tie"):
            lines.append(f"  - {d['higher']} trước {d['lower']}: đồng hạng mọi tiêu chí, xếp theo ID ({d['rule_id']})")
        else:
            lines.append(f"  - {d['higher']} trước {d['lower']} do {d['rule_id']}: "
                         f"{_criterion_text(kb, d['rule_id'], d['higher_info'])} so với "
                         f"{_criterion_text(kb, d['rule_id'], d['lower_info'])}")
    if ranking["excluded"]:
        lines.append("  Không được xếp hạng:")
        for e in ranking["excluded"]:
            why = short_reasons(res, e["id"]) if res is not None else ", ".join(e["reasons"])
            lines.append(f"    ✗ {e['id']}: {STATUS_VI[e['status']]} — {why}")
    return lines
