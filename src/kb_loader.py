"""Nạp cơ sở tri thức (4 tệp JSON trong kb/) và cung cấp truy vấn trên Facts.

Module này chỉ đọc và đánh chỉ mục tri thức; không chứa luật suy diễn.
Ngữ nghĩa ba giá trị của quan hệ (true / false / unknown) theo
``relations.json#negative_rules``:

- có cạnh khẳng định trong ``edges``                -> true
- có cạnh phủ định tường minh trong ``negative_edges`` -> false
- quan hệ có ``negative_rules`` với ``status_attribute``:
  thuộc tính trạng thái của subject = ``complete``   -> false
  ngược lại                                          -> unknown
- quan hệ không khai báo ``negative_rules``          -> false (thế giới đóng
  trên khai báo đầu vào; trạng thái ``unknown`` của hồ sơ do R05 xử lý).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent.parent / "kb"
KB_FILES = {
    "concepts": "concepts.json",
    "relations": "relations.json",
    "facts": "facts.json",
    "rules": "rules.json",
}

TRUE, FALSE, UNKNOWN = "true", "false", "unknown"


class KBLoadError(Exception):
    """Không đọc được một tệp CSTT (thiếu tệp hoặc JSON sai cú pháp)."""


def load_raw(kb_dir: Path | str = KB_DIR) -> dict:
    """Đọc 4 tệp JSON, trả về dict {concepts, relations, facts, rules}."""
    kb_dir = Path(kb_dir)
    raw = {}
    for key, filename in KB_FILES.items():
        path = kb_dir / filename
        try:
            with path.open(encoding="utf-8") as fh:
                raw[key] = json.load(fh)
        except FileNotFoundError as exc:
            raise KBLoadError(f"Thiếu tệp {path}") from exc
        except json.JSONDecodeError as exc:
            raise KBLoadError(
                f"{path}: JSON sai cú pháp tại dòng {exc.lineno}, cột {exc.colno}: {exc.msg}"
            ) from exc
    return raw


class KnowledgeBase:
    """Chỉ mục trên dữ liệu thô đã nạp. Không sửa dữ liệu gốc."""

    def __init__(self, raw: dict):
        self.raw = raw
        self.concepts = {c["id"]: c for c in raw["concepts"]["concepts"]}
        self.relations = {r["name"]: r for r in raw["relations"]["relations"]}

        rules_doc = raw["rules"]
        self.rules = list(rules_doc["rules"])
        self.rule_by_id = {r["id"]: r for r in self.rules}
        self.evaluation_plan = rules_doc.get("evaluation_plan", [])
        self.status_order = rules_doc.get("status_order", [])
        self.comparison_basis = rules_doc.get("comparison_basis", {})

        facts = raw["facts"]
        self.entities: dict[str, dict] = {}
        self.concept_of: dict[str, str] = {}
        self.by_concept: dict[str, list[dict]] = defaultdict(list)
        for concept_id, items in facts["entities"].items():
            for item in items:
                self.entities[item["id"]] = item
                self.concept_of[item["id"]] = concept_id
                self.by_concept[concept_id].append(item)

        self.edges = facts["edges"]
        self.negative_edges = facts.get("negative_edges", [])
        self.sources = {s["id"]: s for s in facts.get("sources", [])}
        self.edge_by_id = {e["id"]: e for e in self.edges}
        self.negative_by_id = {e["id"]: e for e in self.negative_edges}

        self._by_rel = defaultdict(list)
        self._out = defaultdict(list)
        self._in = defaultdict(list)
        self._pos = {}
        for e in self.edges:
            key = (e["relation"], e["subject_id"], e["object_id"])
            self._by_rel[e["relation"]].append(e)
            self._out[(e["relation"], e["subject_id"])].append(e)
            self._in[(e["relation"], e["object_id"])].append(e)
            self._pos.setdefault(key, e)
        self._neg = {}
        for e in self.negative_edges:
            self._neg.setdefault((e["relation"], e["subject_id"], e["object_id"]), e)

        # (food_id, nutrient_id) -> bản ghi nutrient_content
        self._content = {}
        owner = {e["object_id"]: e["subject_id"] for e in self._by_rel["has_nutrient_content"]}
        for e in self._by_rel["measures_nutrient"]:
            nc_id, nutrient_id = e["subject_id"], e["object_id"]
            food_id = owner.get(nc_id)
            if food_id is not None and nc_id in self.entities:
                self._content[(food_id, nutrient_id)] = self.entities[nc_id]

    @classmethod
    def from_dir(cls, kb_dir: Path | str = KB_DIR) -> "KnowledgeBase":
        return cls(load_raw(kb_dir))

    # ----- thực thể -----------------------------------------------------
    def entity(self, entity_id: str) -> dict | None:
        return self.entities.get(entity_id)

    def name(self, entity_id: str) -> str:
        item = self.entities.get(entity_id)
        return item.get("name", entity_id) if item else entity_id

    def items(self, concept_id: str) -> list[dict]:
        return self.by_concept.get(concept_id, [])

    def attr(self, entity_id: str, path: str):
        """Giá trị thuộc tính theo đường dẫn chấm, ví dụ ``context.sex``; thiếu -> None."""
        value = self.entities.get(entity_id)
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    # ----- quan hệ ------------------------------------------------------
    def edges_of(self, relation: str) -> list[dict]:
        return self._by_rel.get(relation, [])

    def objects(self, relation: str, subject_id: str) -> list[dict]:
        return self._out.get((relation, subject_id), [])

    def subjects(self, relation: str, object_id: str) -> list[dict]:
        return self._in.get((relation, object_id), [])

    def edge(self, relation: str, subject_id: str, object_id: str) -> dict | None:
        return self._pos.get((relation, subject_id, object_id))

    def holds(self, relation: str, subject_id: str, object_id: str) -> tuple[str, str]:
        """Trả về (giá trị chân lý, tiền đề) của relation(subject, object)."""
        edge = self._pos.get((relation, subject_id, object_id))
        if edge:
            return TRUE, edge["id"]
        negative = self._neg.get((relation, subject_id, object_id))
        if negative:
            return FALSE, negative["id"]
        spec = self.relations.get(relation, {})
        policies = [p for p in spec.get("negative_rules", []) if p.get("status_attribute")]
        if not policies:
            return FALSE, f"không có cạnh {relation}({subject_id}, {object_id})"
        attribute = policies[0]["status_attribute"]
        status = self.attr(subject_id, attribute)
        premise = f"{subject_id}.{attribute}={status}"
        return (FALSE if status == "complete" else UNKNOWN), premise

    # ----- dinh dưỡng ---------------------------------------------------
    def nutrient_content(self, food_id: str, nutrient_id: str) -> dict | None:
        return self._content.get((food_id, nutrient_id))

    def nutrient_value(self, food_id: str, nutrient_id: str):
        """Giá trị trên 100 g; None nếu chưa biết hoặc không có bản ghi."""
        record = self._content.get((food_id, nutrient_id))
        if record is None or record.get("status") != "known":
            return None
        return record.get("value")

    def nutrient_unit(self, nutrient_id: str) -> str:
        return self.attr(nutrient_id, "unit") or ""

    def group_of(self, food_id: str) -> str | None:
        edges = self.objects("belongs_to_group", food_id)
        return edges[0]["object_id"] if edges else None
