"""CLI nạp CSTT, truy vấn và minh họa suy luận có giải thích.

Ví dụ:
  python src/demo_queries.py demo                         # kịch bản minh họa đầy đủ
  python src/demo_queries.py users                        # danh sách hồ sơ mẫu
  python src/demo_queries.py lookup food_rice_cooked      # tra cứu thực phẩm
  python src/demo_queries.py check user_minh menu_ordinary
  python src/demo_queries.py nutrients dish_rice_chicken
  python src/demo_queries.py recommend user_minh --level menu
  python src/demo_queries.py compare user_minh dish_rice_chicken dish_chickpea_salad
  python src/demo_queries.py rules
Thêm --json để in kết quả máy đọc được; --kb THU_MUC để dùng CSTT khác.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import Engine, KBValidationError  # noqa: E402
from explain import (DISCLAIMER, explain_nutrients, explain_ranking, explain_status,  # noqa: E402
                     explain_user_values)
from kb_loader import KB_DIR, KBLoadError, KnowledgeBase  # noqa: E402
from validate_kb import errors_only, summary, validate  # noqa: E402

LEVELS = ("food", "dish", "meal", "menu")


def _print(lines):
    for line in lines:
        print(line)


def _require(kb, item_id, concepts=None):
    concept = kb.concept_of.get(item_id)
    if concept is None or (concepts and concept not in concepts):
        want = "/".join(concepts) if concepts else "thực thể"
        raise SystemExit(f"Lỗi: {item_id!r} không phải {want} trong CSTT")


def lookup_food(kb: KnowledgeBase, food_id: str) -> dict:
    food = kb.entity(food_id)
    allergens = {}
    for a in kb.items("allergen"):
        truth, premise = kb.holds("contains_allergen", food_id, a["id"])
        allergens[a["id"]] = {"truth": truth, "premise": premise}
    diets = {}
    for d in kb.items("diet_pattern"):
        truth, premise = kb.holds("compatible_with_diet", food_id, d["id"])
        diets[d["id"]] = {"truth": truth, "premise": premise}
    nutrients = {}
    for n in kb.items("nutrient"):
        record = kb.nutrient_content(food_id, n["id"])
        nutrients[n["id"]] = {"value": record.get("value") if record else None, "unit": n["unit"],
                              "status": record.get("status") if record else "unknown",
                              "record_id": record["id"] if record else None,
                              "source_record_id": record.get("source_record_id") if record else None}
    return {"id": food_id, "name": food["name"], "food_state": food["food_state"], "origin": food["origin"],
            "group_id": kb.group_of(food_id), "fdc_id": food.get("_meta", {}).get("fdc_id"),
            "basis": "100 g phần ăn được", "allergens": allergens, "diets": diets, "nutrients": nutrients}


def print_lookup(kb, data):
    print(f"{data['id']} — {data['name']}")
    print(f"  trạng thái: {data['food_state']}; nguồn gốc: {data['origin']}; nhóm (REL01): {data['group_id']}; "
          f"USDA FDC {data['fdc_id']}")
    print("  dị ứng (REL05): " + ", ".join(f"{a}={v['truth']}" for a, v in data["allergens"].items()))
    print("  chế độ ăn (REL08): " + ", ".join(f"{d}={v['truth']}" for d, v in data["diets"].items()))
    print(f"  hàm lượng trên {data['basis']}:")
    for nid, v in data["nutrients"].items():
        value = "null" if v["value"] is None else v["value"]
        print(f"    {kb.name(nid):30} {value!s:>8} {v['unit']:4} [{v['record_id']}; USDA {v['source_record_id']}]")


def profile_lines(kb, res) -> list[str]:
    uid = res.user_id
    user = kb.entity(uid)
    ctx = user["context"]
    lines = [f"{uid} — {user['name']}: {ctx.get('age')} tuổi, {ctx.get('sex')}, vận động {ctx.get('activity')}"
             + (f", {ctx['weight_kg']} kg, {ctx['height_cm']} cm" if "weight_kg" in ctx and "height_cm" in ctx else ""),
             f"  mục tiêu: {user['nutrition_goal']}; allergy_status={user['allergy_status']}; "
             f"avoid_status={user['avoid_status']}"]
    rel = lambda name: [e["object_id"] for e in kb.objects(name, uid)]  # noqa: E731
    prefs = [f"{e['object_id']}({e['attributes']['preference']})" for e in kb.objects("prefers_food", uid)]
    lines.append(f"  chế độ: {', '.join(rel('follows_diet'))}; dị ứng: {', '.join(rel('allergic_to')) or '—'}; "
                 f"tránh: {', '.join(rel('avoids_food')) or '—'}; sở thích: {', '.join(prefs) or '—'}")
    lines.extend(explain_user_values(res))
    return lines


def run_demo(engine: Engine, kb: KnowledgeBase):
    s = summary(kb.raw)
    issues = validate(kb.raw)
    print("=" * 78)
    print("1. NẠP VÀ KIỂM TRA CSTT")
    print(f"   {s['concepts']} concepts, {s['relations']} relations, {s['rules']} luật, "
          f"{sum(s['entities'].values())} thực thể, {s['edges']} cạnh, {s['negative_edges']} cạnh phủ định")
    print(f"   validate_kb: {len(errors_only(issues))} lỗi, {len(issues) - len(errors_only(issues))} cảnh báo")
    print("=" * 78)
    print("2. TRA CỨU TRI THỨC: food_rice_cooked")
    print_lookup(kb, lookup_food(kb, "food_rice_cooked"))
    print("=" * 78)
    print("3. GỢI Ý THỰC ĐƠN CHO TỪNG HỒ SƠ MẪU")
    for user in kb.items("user_profile"):
        res, ranking = engine.recommend(user["id"], "menu")
        print("-" * 78)
        _print(profile_lines(kb, res))
        _print(explain_ranking(kb, ranking, res))
    print("=" * 78)
    print("4. GIẢI THÍCH CHI TIẾT")
    cases = [("user_minh", "menu_ordinary", "dị ứng sữa lan truyền từ nguyên liệu lên thực đơn"),
             ("user_huy", "food_peanut_roasted", "dị ứng luôn bị loại dù người dùng thích"),
             ("user_quang", "dish_rice_chicken", "cần tránh + thuần chay thắng sở thích"),
             ("user_vy", "dish_fruit_plate", "thiếu khai báo dị ứng -> không kết luận đủ điều kiện")]
    for uid, item, title in cases:
        if kb.entity(uid) and kb.entity(item):
            print(f"-- {title}")
            _print(explain_status(engine.infer(uid), item))
    print("-- tổng hợp dinh dưỡng (R06) và giá trị thiếu giữ null")
    res = engine.infer("user_minh")
    _print(explain_nutrients(res, "dish_rice_chicken"))
    _print(explain_nutrients(res, "menu_milk_free"))
    print("=" * 78)
    print(DISCLAIMER)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Truy vấn và minh họa suy luận trên CSTT dinh dưỡng.")
    parser.add_argument("--kb", default=str(KB_DIR), help="thư mục CSTT (mặc định: kb/)")
    parser.add_argument("--json", action="store_true", help="in kết quả dạng JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="kịch bản minh họa đầy đủ")
    sub.add_parser("users", help="liệt kê hồ sơ người dùng")
    sub.add_parser("rules", help="liệt kê luật trong CSTT")
    p = sub.add_parser("lookup", help="tra cứu một thực phẩm")
    p.add_argument("food_id")
    p = sub.add_parser("profile", help="hồ sơ và giá trị suy ra cho người dùng")
    p.add_argument("user_id")
    p = sub.add_parser("check", help="trạng thái và giải thích của một ứng viên cho người dùng")
    p.add_argument("user_id")
    p.add_argument("item_id")
    p.add_argument("--all", action="store_true", help="in mọi lý do gốc")
    p = sub.add_parser("nutrients", help="tổng hợp dinh dưỡng (R06)")
    p.add_argument("item_id")
    p.add_argument("--user", help="kèm tỷ lệ đáp ứng năng lượng cho người dùng")
    p = sub.add_parser("recommend", help="gợi ý và xếp hạng ứng viên cùng cấp")
    p.add_argument("user_id")
    p.add_argument("--level", choices=LEVELS, default="menu")
    p.add_argument("--top", type=int)
    p = sub.add_parser("compare", help="xếp hạng các ứng viên cho trước")
    p.add_argument("user_id")
    p.add_argument("item_ids", nargs="+")
    args = parser.parse_args(argv)

    try:
        kb = KnowledgeBase.from_dir(args.kb)
        engine = Engine(kb)
    except KBLoadError as exc:
        print(f"Lỗi nạp CSTT: {exc}")
        return 1
    except KBValidationError as exc:
        print(f"Lỗi: {exc}. Chạy python src/validate_kb.py để xem chi tiết.")
        return 1

    if args.command == "demo":
        run_demo(engine, kb)
        return 0
    if args.command == "users":
        rows = [{"id": u["id"], "name": u["name"], "goal": u["nutrition_goal"],
                 "diet": [e["object_id"] for e in kb.objects("follows_diet", u["id"])],
                 "allergies": [e["object_id"] for e in kb.objects("allergic_to", u["id"])],
                 "avoid": [e["object_id"] for e in kb.objects("avoids_food", u["id"])],
                 "allergy_status": u["allergy_status"]} for u in kb.items("user_profile")]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for r in rows:
                print(f"{r['id']:12} {r['name']:14} goal={r['goal']:15} diet={','.join(r['diet']):16} "
                      f"dị ứng={','.join(r['allergies']) or '—'} ({r['allergy_status']}) tránh={','.join(r['avoid']) or '—'}")
        return 0
    if args.command == "rules":
        rules = sorted(kb.rules, key=lambda r: r["id"])
        if args.json:
            print(json.dumps([{k: r[k] for k in ("id", "name", "kind", "phase", "priority", "source_ids")}
                              for r in rules], ensure_ascii=False, indent=2))
        else:
            for r in rules:
                print(f"{r['id']}  {r['kind']:11} {r['phase']:16} p={r['priority']:<4} {r['name']}  "
                      f"[{', '.join(r['source_ids'])}]")
        return 0
    if args.command == "lookup":
        _require(kb, args.food_id, ["food"])
        data = lookup_food(kb, args.food_id)
        print(json.dumps(data, ensure_ascii=False, indent=2)) if args.json else print_lookup(kb, data)
        return 0
    if args.command == "nutrients":
        _require(kb, args.item_id, LEVELS)
        res = engine.infer(args.user or kb.items("user_profile")[0]["id"])
        if args.json:
            print(json.dumps({"id": args.item_id, "basis": res.nutrient_basis.get(args.item_id),
                              "nutrients": res.nutrients.get(args.item_id), "missing": res.missing.get(args.item_id),
                              "energy_ratio": res.item_values.get(args.item_id, {}).get("energy_ratio") if args.user else None},
                             ensure_ascii=False, indent=2))
        else:
            lines = explain_nutrients(res, args.item_id)
            _print(lines if args.user else [line for line in lines if "R12" not in line])
        return 0

    _require(kb, args.user_id, ["user_profile"])
    res = engine.infer(args.user_id)
    if args.command == "profile":
        if args.json:
            print(json.dumps({"user": kb.entity(args.user_id), "derived": res.user_values}, ensure_ascii=False, indent=2))
        else:
            _print(profile_lines(kb, res))
    elif args.command == "check":
        _require(kb, args.item_id, LEVELS)
        if args.json:
            print(json.dumps({"user_id": args.user_id, "item_id": args.item_id, "status": res.status(args.item_id),
                              "reasons": res.reasons(args.item_id), "rules_fired": res.rules_fired(args.item_id),
                              "origins": res.origins(args.item_id)}, ensure_ascii=False, indent=2))
        else:
            _print(explain_status(res, args.item_id, limit=10_000 if args.all else 8))
    elif args.command in ("recommend", "compare"):
        if args.command == "compare":
            for item in args.item_ids:
                _require(kb, item, LEVELS)
            try:
                ranking = engine.rank(res, args.item_ids)
            except ValueError as exc:
                raise SystemExit(f"Lỗi: {exc}")
        else:
            ranking = engine.rank(res, concept=args.level)
        if args.json:
            print(json.dumps(ranking, ensure_ascii=False, indent=2, default=str))
        else:
            _print(explain_user_values(res))
            _print(explain_ranking(kb, ranking, res, top=getattr(args, "top", None)))
    if not args.json:
        print(DISCLAIMER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
