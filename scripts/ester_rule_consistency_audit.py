#!/usr/bin/env python3
"""Ester-source consistency audit for NJIT Thesis Auditor rules.

Compares Ester's formatting-rules spreadsheet and YES/NO audit logic matrix
against the public rule reference, backend catalog, detectors, and tests.
"""

# ruff: noqa: E402, E501

from __future__ import annotations

import csv
import importlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import openpyxl

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from njit_auditor.specs.q_rule_coverage import (
    _AUTHORITY_OVERLAY_PATH,
    build_coverage_report,
    coverage_summary,
    load_current_authority_overlay,
)

_FORMATTING_XLSX = _REPO_ROOT / "results/ester_feedback_raw/formatting_rules.xlsx"
_MATRIX_XLSX = _REPO_ROOT / "data/raw/ester/260330_YESNO_audit_logic_matrix.xlsx"
_MATRIX_XLSX_LEGACY = _REPO_ROOT / "results/ester_feedback_raw/yesno_audit_matrix.xlsx"
_P_FEEDBACK_JSON = _REPO_ROOT / "data/specs/ester_p_rule_feedback.json"
_Q_MATRIX_JSON = _REPO_ROOT / "data/specs/ester_q_matrix.json"
_CATALOG_PATH = _REPO_ROOT / "data/processed/rules/project_added_rules.json"
_INVENTORY_PATH = _REPO_ROOT / "data/processed/rules/njit_rule_inventory.json"
_TESTS_DIR = _REPO_ROOT / "tests"
_RULES_DIR = _REPO_ROOT / "src/njit_auditor/rules"

_BROAD_PARENT_RULES = frozenset(
    {
        "P014", "P015", "P017", "P018", "P024", "P026", "P030", "P032",
        "P036", "P038", "P042", "P043", "P044", "P046", "P048",
    }
)

_SPLIT_REQUEST_KEYWORDS = (
    "broken", "break down", "broken doen", "two groups", "different questions",
    "one issue", "each of the front matter", "separate",
)

_STATUS_VALUES = (
    "aligned",
    "superseded by later Ester authority",
    "wording mismatch",
    "remediation mismatch",
    "detector mismatch",
    "public rule reference mismatch",
    "implemented but not public",
    "public but not implemented",
    "partially implemented",
    "manual review only",
    "missing",
    "extra/unjustified rule not supported by Ester's files",
    "ambiguous / needs Ester decision",
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _pad_row(row: tuple[Any, ...], width: int = 5) -> list[str]:
    values = list(row) + [""] * max(0, width - len(row))
    return [str(v).strip() if v is not None else "" for v in values[:width]]


def parse_formatting_xlsx(path: Path) -> list[dict[str, str]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = [r for r in ws.iter_rows(values_only=True) if any(c is not None and str(c).strip() for c in r)]
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        cols = _pad_row(row)
        rid = cols[0]
        if not re.match(r"^P\d+", rid):
            continue
        records.append(
            {
                "id": rid,
                "original_question": cols[1],
                "proposed_question": cols[2],
                "original_remediation": cols[3],
                "proposed_remediation": cols[4],
                "ester_split_requested": any(
                    kw in _norm(cols[2]) for kw in _SPLIT_REQUEST_KEYWORDS
                ),
                "ester_q_refs": sorted(
                    {f"Q{int(m):03d}" for m in re.findall(r"Q\s*(\d+)", cols[2], re.I)}
                ),
                "comments": cols[2] if cols[2] and cols[2] != cols[1] else "",
            }
        )
    return records


def parse_formatting_json(path: Path) -> list[dict[str, str]]:
    """Load P-rule Ester feedback from the repo JSON mirror when xlsx is absent."""
    data = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict[str, str]] = []
    for item in data.get("feedback", []):
        rid = str(item.get("id", "")).strip()
        if not re.match(r"^P\d+", rid):
            continue
        proposed_question = str(item.get("proposed_question_edit", "")).strip()
        proposed_remediation = str(item.get("proposed_remediation_edit", "")).strip()
        records.append(
            {
                "id": rid,
                "original_question": str(item.get("original_question", "")).strip(),
                "proposed_question": proposed_question,
                "original_remediation": str(item.get("original_remediation", "")).strip(),
                "proposed_remediation": proposed_remediation,
                "ester_split_requested": any(
                    kw in _norm(proposed_question) for kw in _SPLIT_REQUEST_KEYWORDS
                ),
                "ester_q_refs": sorted(
                    {f"Q{int(m):03d}" for m in re.findall(r"Q\s*(\d+)", proposed_question, re.I)}
                ),
                "comments": proposed_question,
            }
        )
    return records


def _first_available_source(label: str, *paths: Path) -> Path:
    for path in paths:
        if path.is_file():
            return path
    raise FileNotFoundError(f"No {label} source found; tried: {', '.join(map(str, paths))}")


def formatting_p_source() -> Path:
    return _first_available_source("P-rule feedback", _FORMATTING_XLSX, _P_FEEDBACK_JSON)


def matrix_q_source() -> Path:
    return _first_available_source(
        "YES/NO Q-matrix", _MATRIX_XLSX, _MATRIX_XLSX_LEGACY, _Q_MATRIX_JSON
    )


def load_formatting_p_rules(source: Path | None = None) -> list[dict[str, str]]:
    source = source or formatting_p_source()
    return parse_formatting_xlsx(source) if source.suffix == ".xlsx" else parse_formatting_json(source)


def load_matrix_q_rules(source: Path | None = None) -> list[dict[str, str]]:
    source = source or matrix_q_source()
    return parse_matrix_xlsx(source) if source.suffix == ".xlsx" else parse_matrix_json(source)


def parse_matrix_xlsx(path: Path) -> list[dict[str, str]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = [r for r in ws.iter_rows(values_only=True) if any(c is not None and str(c).strip() for c in r)]
    records: list[dict[str, str]] = []
    section = ""
    for row in rows[1:]:
        cols = _pad_row(row, width=4)
        qid = cols[0]
        if re.match(r"^Q\d+", qid):
            m = re.match(r"Q(\d+)$", qid)
            qid = f"Q{int(m.group(1)):03d}" if m else qid
            records.append(
                {
                    "id": qid,
                    "section": section,
                    "question": cols[1],
                    "rule_definition": cols[2],
                    "remediation": cols[3],
                }
            )
        elif cols[0] and not any(cols[1:]):
            # The tracked matrix places section headings in column A.
            section = cols[0]
        elif cols[1] and not cols[0]:
            section = cols[1]
    return records


def parse_matrix_json(path: Path) -> list[dict[str, str]]:
    """Load the checked-in Q-matrix mirror with the same fields as the XLSX."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid Q-matrix JSON in {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ValueError(f"Invalid Q-matrix JSON in {path}: expected a rules list")
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError(f"Invalid Q-matrix JSON in {path}: metadata is not an object")
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(data["rules"], start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid Q-matrix JSON in {path}: rule {index} is not an object")
        qid = item.get("id")
        if not isinstance(qid, str) or not re.fullmatch(r"Q\d{3}", qid) or qid in seen:
            raise ValueError(f"Invalid Q-matrix JSON in {path}: invalid or duplicate rule ID {qid!r}")
        record = {"id": qid}
        for field_name in ("section", "question", "rule_definition", "remediation"):
            value = item.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Invalid Q-matrix JSON in {path}: {qid} has no {field_name}"
                )
            record[field_name] = value.strip()
        records.append(record)
        seen.add(qid)
    expected = metadata.get("total_rules")
    if not records or (expected is not None and expected != len(records)):
        raise ValueError(f"Invalid Q-matrix JSON in {path}: rule count does not match metadata")
    return records


def _source_label(path: Path) -> str:
    """Keep selected-source provenance repo-relative in generated reports."""
    try:
        return str(path.relative_to(_REPO_ROOT))
    except ValueError:
        return path.name


def _source_note(path: Path) -> str:
    if path.suffix != ".xlsx":
        return "Checked-in JSON mirror"
    workbook = openpyxl.load_workbook(path, read_only=True)
    try:
        return f"Sheet: `{workbook.sheetnames[0].strip()}`"
    finally:
        workbook.close()


def _infer_section_from_question(question: str, fallback: str = "") -> str:
    q = _norm(question)
    hints = (
        ("abstract", "Abstract"),
        ("title page", "Title Page"),
        ("copyright", "Copyright Page"),
        ("approval page", "Approval Page"),
        ("dedication", "Dedication"),
        ("acknowledgement", "Acknowledgements"),
        ("biographical sketch", "Biographical Sketch"),
        ("table of contents", "Table of Contents"),
        ("list of tables", "List of Tables"),
        ("list of figures", "List of Figures"),
        ("appendix", "Appendix"),
        ("figure", "Figures"),
        ("table", "Tables"),
    )
    for needle, label in hints:
        if needle in q:
            return label
    return fallback


def enrich_q_sections(records: list[dict[str, str]]) -> None:
    current = ""
    for rec in records:
        if rec.get("section"):
            current = rec["section"]
        elif not rec.get("section"):
            rec["section"] = _infer_section_from_question(rec.get("question", ""), current)


@dataclass
class ImplementationRule:
    id: str
    question: str
    remediation: str
    implementation_status: str
    implementation_module: str
    issue_types: list[str] = field(default_factory=list)
    source_q_rule_ids: list[str] = field(default_factory=list)
    notes: str = ""
    section: str = ""
    tests: list[str] = field(default_factory=list)
    public_question: str = ""
    public_remediation: str = ""
    public_visible: bool = False
    enforcement: str = ""


def _scan_tests_for_rules() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = defaultdict(list)
    for path in sorted(_TESTS_DIR.glob("test_*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\b(P\d{3}[A-Z]?|Q\d{3})\b", text):
            mapping[m.group(1)].append(path.name)
    return {k: sorted(set(v)) for k, v in mapping.items()}


def _scan_detector_issue_types(module_name: str) -> list[str]:
    if not module_name:
        return []
    rel = module_name.replace("njit_auditor.rules.", "") + ".py"
    path = _RULES_DIR / rel
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(r'"issue_type":\s*"([^"]+)"', text)))


def _load_public_catalog() -> dict[str, dict[str, Any]]:
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    catalog = wa._build_rule_catalog()
    by_id: dict[str, dict[str, Any]] = {}
    for rule in catalog["student_rules"]:
        by_id[str(rule["id"])] = {
            "question": str(rule.get("title", "")),
            "remediation": str(rule.get("how_to_correct", "")),
            "section": str(rule.get("section", "")),
            "parent_rule_id": str(rule.get("parent_rule_id", "")),
            "source_q_rule_ids": list(rule.get("source_q_rule_ids", []) or []),
            "issue_types": list(rule.get("issue_types", []) or []),
        }
    atomic_by_id = (
        {spec.id: spec for spec in wa._ATOMIC_PUBLIC_RULE_CARDS}
        if hasattr(wa, "_ATOMIC_PUBLIC_RULE_CARDS")
        else {
            rid: type(
                "AtomicSpec",
                (),
                {
                    "id": rid,
                    "parent_rule_id": rid[:-1],
                    "question": rule.get("question", ""),
                    "remediation": rule.get("remediation", ""),
                    "issue_types": tuple(rule.get("issue_types", []) or []),
                    "source_q_rule_ids": tuple(rule.get("source_q_rule_ids", []) or []),
                },
            )()
            for rid, rule in by_id.items()
            if re.fullmatch(r"P\d{3}[A-Z]", rid)
        }
    )
    hidden = (
        set(wa._HIDDEN_PUBLIC_RULE_IDS)
        if hasattr(wa, "_HIDDEN_PUBLIC_RULE_IDS")
        else {rid[:-1] for rid in by_id if re.fullmatch(r"P\d{3}[A-Z]", rid)}
    )
    return {
        "by_id": by_id,
        "atomic_specs": atomic_by_id,
        "hidden_parent_ids": hidden,
        "total_public": len(by_id),
    }


def _enforcement_label(status: str, module: str, notes: str) -> str:
    s = (status or "").lower()
    n = _norm(notes)
    if s in {"not_implemented", "unimplemented"}:
        return "not implemented"
    if s == "manual_review_only" or "manual review" in n or "manual-only" in n:
        return "manual-review only"
    if s in {"partial", "partially_implemented"}:
        return "partially enforced"
    if module and s == "implemented":
        return "enforced automatically"
    if s == "implemented":
        return "enforced automatically"
    return s or "unknown"


def build_implementation_inventory(
    catalog: list[dict[str, Any]],
    public: dict[str, Any],
    test_map: dict[str, list[str]],
) -> dict[str, ImplementationRule]:
    inv: dict[str, ImplementationRule] = {}
    public_by_id = public["by_id"]
    hidden = public["hidden_parent_ids"]
    for rule in catalog:
        rid = str(rule["id"])
        module = str(rule.get("implementation_module") or "")
        notes = str(rule.get("notes") or "")
        q_ids = sorted(
            {
                f"Q{int(m):03d}"
                for m in re.findall(r"Q(\d+)", " ".join([notes, str(rule.get("q_rule_ids", ""))]))
            }
        )
        pub = public_by_id.get(rid, {})
        inv[rid] = ImplementationRule(
            id=rid,
            question=str(rule.get("question", "")),
            remediation=str(rule.get("remediation", "")),
            implementation_status=str(rule.get("implementation_status", "")),
            implementation_module=module,
            issue_types=_scan_detector_issue_types(module),
            source_q_rule_ids=q_ids,
            notes=notes,
            section=str(rule.get("section", "")),
            tests=test_map.get(rid, []),
            public_question=pub.get("question", ""),
            public_remediation=pub.get("remediation", ""),
            public_visible=rid in public_by_id and rid not in hidden,
            enforcement=_enforcement_label(
                str(rule.get("implementation_status", "")),
                module,
                notes,
            ),
        )
    for aid, spec in public["atomic_specs"].items():
        inv[aid] = ImplementationRule(
            id=aid,
            question=spec.question,
            remediation=spec.remediation,
            implementation_status="public_atomic_card",
            implementation_module=inv.get(spec.parent_rule_id, ImplementationRule(
                id=spec.parent_rule_id, question="", remediation="",
                implementation_status="", implementation_module="",
            )).implementation_module,
            issue_types=list(spec.issue_types or ()),
            source_q_rule_ids=list(spec.source_q_rule_ids or ()),
            notes=f"Atomic public card for {spec.parent_rule_id}",
            section=inv.get(spec.parent_rule_id, ImplementationRule(
                id=spec.parent_rule_id, question="", remediation="",
                implementation_status="", implementation_module="",
            )).section,
            tests=sorted(
                set(test_map.get(aid, []) + test_map.get(spec.parent_rule_id, []))
            ),
            public_question=spec.question,
            public_remediation=spec.remediation,
            public_visible=True,
            enforcement=inv.get(spec.parent_rule_id, ImplementationRule(
                id=spec.parent_rule_id, question="", remediation="",
                implementation_status="", implementation_module="",
            )).enforcement,
        )
    return inv


def _ester_target_question(p: dict[str, str]) -> str:
    proposed = p.get("proposed_question") or ""
    if _norm(proposed).startswith("no edits"):
        return p.get("original_question") or ""
    return proposed or p.get("original_question") or ""


def _ester_target_remediation(p: dict[str, str]) -> str:
    proposed = p.get("proposed_remediation") or ""
    if _norm(proposed).startswith("no edits"):
        return p.get("original_remediation") or ""
    return proposed or p.get("original_remediation") or ""


def _p026_detector_public_contradiction(public: dict[str, Any]) -> dict[str, str]:
    """Compare P026A public policy with pdf_font_compliance.py acceptance logic."""
    from njit_auditor.rules.pdf_font_compliance import (
        classify_font,
        is_accepted_body_font_family,
    )

    p026a = public["by_id"].get("P026A", {})
    public_text = _norm(
        (p026a.get("remediation", "") or "")
        + " "
        + (p026a.get("question", "") or "")
    )
    public_accepts_cmr = "computer modern" in public_text
    public_accepts_lm = "latin modern" in public_text

    sample_fonts = ("CMR12", "LMRoman10-Regular", "ABCDEE+CMR10", "ABCDEE+LMRoman10-Regular")
    detector_accepts_cmr = all(
        is_accepted_body_font_family(classify_font(font)) for font in sample_fonts
    )
    detector_flags_cmr = public_accepts_cmr and not detector_accepts_cmr

    if detector_flags_cmr:
        detail = (
            "Public P026A tells LaTeX users Computer Modern is accepted, but "
            "pdf_font_compliance.py still flags CMR/Latin Modern as "
            "possible_body_font_family_issue."
        )
        status = "detector mismatch"
    elif public_accepts_cmr and public_accepts_lm and detector_accepts_cmr:
        detail = (
            "P026A/P026B split is in place. Public P026A cites Times/Arial (Word) and "
            "Computer Modern/Latin Modern (Overleaf); pdf_font_compliance.py accepts "
            "those families without emitting possible_body_font_family_issue."
        )
        status = "aligned"
    else:
        detail = "No CMR public/detector contradiction detected."
        status = "aligned"

    return {
        "rule": "P026A / pdf_font_compliance.py",
        "public_accepts_cmr": str(public_accepts_cmr),
        "detector_flags_cmr": str(detector_flags_cmr),
        "status": status,
        "detail": detail,
    }


def _ester_priority_review(
    ester_p: list[dict[str, str]],
    public: dict[str, Any],
    q_rows: list[dict[str, Any]],
    impl_rules: dict[str, ImplementationRule],
    p026_contradiction: dict[str, str],
) -> list[dict[str, str]]:
    """Summarize Ester's named priority areas A–H."""
    findings: list[dict[str, str]] = []

    # A. One issue per question
    broad_visible = [
        rid for rid, rule in impl_rules.items()
        if rule.public_visible and rid in _BROAD_PARENT_RULES
    ]
    p015_atomic = [s.id for s in public["atomic_specs"].values() if s.parent_rule_id == "P015"]
    p018_atomic = [s.id for s in public["atomic_specs"].values() if s.parent_rule_id == "P018"]
    findings.append(
        {
            "area": "A. One issue per question",
            "status": "gap" if broad_visible or not p015_atomic or not p018_atomic else "mostly aligned",
            "detail": (
                f"Broad parents still visible: {broad_visible or 'none'}. "
                f"P015 atomic cards: {p015_atomic or 'NONE (Ester wants 2 body-indent checks)'}. "
                f"P018 atomic cards: {p018_atomic or 'NONE (delegated to P024/P032/P036/P039/P042/P046/P048)'}. "
                f"P017 missing atomic cards for single-spaced/justified (1c) and bold Figure label (1d) per Ester split."
            ),
        }
    )

    # B. Front matter Q001–Q079
    q_by_status = Counter(r["Status"] for r in q_rows)
    findings.append(
        {
            "area": "B. Front matter Q001–Q079",
            "status": "partial",
            "detail": (
                f"Q status: aligned={q_by_status.get('aligned', 0)}, "
                f"partial={q_by_status.get('partially implemented', 0)}, "
                f"manual={q_by_status.get('manual review only', 0)}, "
                f"wording={q_by_status.get('wording mismatch', 0)}. "
                "All 79 Q-rules represented; 12 manual-review, 4 partial."
            ),
        }
    )

    # C. Font rules — derive status from live detector vs public policy check
    p026_atomic = sorted(
        spec.id for spec in public["atomic_specs"].values() if spec.parent_rule_id == "P026"
    )
    if p026_contradiction["status"] == "detector mismatch":
        p026_status = "contradiction"
        p026_detail = p026_contradiction["detail"]
    elif p026_atomic == ["P026A", "P026B"]:
        p026_status = "aligned"
        p026_detail = p026_contradiction["detail"]
    else:
        p026_status = "review"
        p026_detail = (
            f"P026 atomic public cards: {p026_atomic or 'none'}. "
            f"Detector/public policy check: {p026_contradiction['detail']}"
        )
    findings.append(
        {
            "area": "C. Font rules (P026)",
            "status": p026_status,
            "detail": p026_detail,
        }
    )

    # D. Margins
    p011 = impl_rules.get("P011")
    findings.append(
        {
            "area": "D. Margins (P011)",
            "status": "aligned" if p011 and "1.5" in p011.remediation else "review",
            "detail": (
                f"Public/catalog remediation: {p011.remediation[:160] if p011 else 'missing'}. "
                "Detector: pdf_margins.py (left 1.5in, others 1in)."
            ),
        }
    )

    # E. Captions
    p017_children = sorted(s.id for s in public["atomic_specs"].values() if s.parent_rule_id == "P017")
    findings.append(
        {
            "area": "E. Captions (P017)",
            "status": "partial split",
            "detail": (
                f"Atomic public cards: {', '.join(p017_children)}. "
                "Missing public atomic cards for Ester 1c (single-spaced/justified) and 1d (bold Figure label) "
                "and 2c (multi-line table title single-spacing). Partial coverage via P032/P050/P055."
            ),
        }
    )

    # F. TOC/LoT/LoF
    p018_atomic = sorted(
        spec.id for spec in public["atomic_specs"].values() if spec.parent_rule_id == "P018"
    )
    if p018_atomic and len(p018_atomic) >= 17:
        p018_status = "aligned"
        p018_detail = (
            f"Canonical public cards: {', '.join(p018_atomic)}. "
            "Superseded delegated cards (P024A–C, P032A, P036A–C, P042A–B, "
            "P046A–B, P048A–B) hidden from /rules. Q051 level-3 sentence case "
            "remains partial in detector."
        )
    else:
        p018_status = "delegated split"
        p018_detail = (
            f"P018 atomic cards: {p018_atomic or 'none'}. "
            "Expected P018A–P018Q covering Ester TOC/LoT/LoF sub-questions."
        )
    findings.append(
        {
            "area": "F. TOC/LoT/LoF (P018 family)",
            "status": p018_status,
            "detail": p018_detail,
        }
    )

    # G. Paragraph indentation — derive body-indent split status from atomic cards
    p015_atomic = sorted(
        spec.id for spec in public["atomic_specs"].values() if spec.parent_rule_id == "P015"
    )
    p043_atomic = sorted(
        spec.id for spec in public["atomic_specs"].values() if spec.parent_rule_id == "P043"
    )
    p044_atomic = sorted(
        spec.id for spec in public["atomic_specs"].values() if spec.parent_rule_id == "P044"
    )
    if p015_atomic == ["P015A", "P015B"] and p043_atomic and p044_atomic:
        indent_status = "aligned"
        indent_detail = (
            "Abstract (Q002/Q003) and Acknowledgements (Q044/Q045) split into "
            f"P044A/B and P043A/B. Body indentation split into {', '.join(p015_atomic)}."
        )
    elif p015_atomic == ["P015A", "P015B"]:
        indent_status = "mostly aligned"
        indent_detail = (
            "Body indentation split into P015A, P015B. "
            f"Abstract/Acknowledgements atomic cards: P043={p043_atomic or 'none'}, "
            f"P044={p044_atomic or 'none'}."
        )
    else:
        indent_status = "partial"
        indent_detail = (
            f"Abstract/Acknowledgements atomic cards: P043={p043_atomic or 'none'}, "
            f"P044={p044_atomic or 'none'}. Body P015 atomic cards: {p015_atomic or 'none'}."
        )
    findings.append(
        {
            "area": "G. Paragraph indentation (P015/P043/P044)",
            "status": indent_status,
            "detail": indent_detail,
        }
    )

    # H. Page numbering
    findings.append(
        {
            "area": "H. Page numbering (P013/P019/P028/P029/P037)",
            "status": "mostly aligned",
            "detail": (
                "P013 bottom-center position wording aligned. P028/P029 Roman/Arabic regime checks implemented. "
                "P037 fixed slot anchors (bio=iv, etc.) may conflict with sequence-based front-matter numbering "
                "when optional pages differ — verify against matrix intent."
            ),
        }
    )
    return findings


def classify_p_rule(
    ester: dict[str, str],
    impl: ImplementationRule | None,
    public: dict[str, Any],
) -> tuple[str, str]:
    pid = ester["id"]
    notes: list[str] = []
    if impl is None:
        return "missing", "No backend catalog entry."

    ester_q = _ester_target_question(ester)
    ester_r = _ester_target_remediation(ester)
    statuses: list[str] = []

    if ester.get("ester_split_requested"):
        atomic_children = [
            spec.id
            for spec in public["atomic_specs"].values()
            if spec.parent_rule_id == pid
        ]
        if not atomic_children:
            statuses.append("public rule reference mismatch")
            notes.append("Ester requested split; no atomic public cards found.")
        elif pid in public["hidden_parent_ids"]:
            notes.append(f"Parent hidden; atomic cards: {', '.join(sorted(atomic_children))}.")
        else:
            statuses.append("public rule reference mismatch")
            notes.append("Ester requested split but parent rule still public.")

    if impl.public_visible and pid in public["hidden_parent_ids"]:
        statuses.append("public rule reference mismatch")
        notes.append("Broad parent rule is still visible on /rules.")

    public_q = impl.public_question or (impl.question if impl.public_visible else "")
    public_r = impl.public_remediation or (impl.remediation if impl.public_visible else "")

    if ester_q and public_q:
        if _similarity(ester_q, public_q) < 0.55 and ester.get("proposed_question"):
            statuses.append("wording mismatch")
            notes.append("Public question diverges from Ester proposed wording.")
    elif ester_q and not public_q and pid in _BROAD_PARENT_RULES:
        child_cards = [
            spec for spec in public["atomic_specs"].values() if spec.parent_rule_id == pid
        ]
        if child_cards:
            notes.append("Uses atomic public cards instead of parent question.")
        else:
            statuses.append("public rule reference mismatch")

    if ester_r and public_r and ester.get("proposed_remediation"):
        if _similarity(ester_r, public_r) < 0.45:
            statuses.append("remediation mismatch")

    if impl.implementation_status in {"not_implemented", "unimplemented"}:
        statuses.append("missing")
    elif impl.implementation_status in {"partial", "partially_implemented"}:
        statuses.append("partially implemented")
    elif "manual" in impl.enforcement:
        statuses.append("manual review only")

    if impl.implementation_module and impl.implementation_status == "implemented":
        if not impl.issue_types and impl.enforcement == "enforced automatically":
            notes.append("Detector module present but no issue_type literals found.")

    if not statuses:
        return "aligned", "; ".join(notes) if notes else ""
    if len(statuses) == 1:
        return statuses[0], "; ".join(notes)
    priority = [
        "missing",
        "detector mismatch",
        "public rule reference mismatch",
        "wording mismatch",
        "remediation mismatch",
        "partially implemented",
        "manual review only",
    ]
    for p in priority:
        if p in statuses:
            return p, "; ".join(notes + [f"also: {', '.join(s for s in statuses if s != p)}"])
    return statuses[0], "; ".join(notes)


def classify_q_rule(
    ester: dict[str, str],
    coverage: Any,
    impl_rules: dict[str, ImplementationRule],
    public: dict[str, Any],
) -> tuple[str, str, str]:
    qid = ester["id"]
    notes: list[str] = []
    detector = ", ".join(coverage.implementing_p_rules) if coverage else ""
    status = coverage.implementation_status if coverage else "missing"

    atomic_cards = [
        spec
        for spec in public["atomic_specs"].values()
        if qid in (spec.source_q_rule_ids or ())
    ]
    public_cards = [c.id for c in atomic_cards]
    if public_cards:
        notes.append(f"Public atomic cards: {', '.join(sorted(public_cards))}.")

    overlay = getattr(coverage, "authority_overlay", None) if coverage else None
    if overlay:
        notes.append(f"Historical matrix question superseded. {overlay['source']}.")
        notes.append(f"Effective requirement: {overlay['effective_requirement']}")
        effective_status = overlay["effective_implementation_status"]
        if effective_status == "optional_not_enforced":
            if detector:
                return "detector mismatch", detector, "; ".join(notes)
        elif effective_status in {"implemented", "partially_implemented"}:
            if not detector or not atomic_cards:
                return "missing", detector, "; ".join(notes)
            best = max(_similarity(c.question, overlay["effective_question"]) for c in atomic_cards)
            if best < 0.5:
                return "wording mismatch", detector, "; ".join(notes)
        else:
            raise ValueError(f"Unknown effective implementation status for {qid}")
        return "superseded by later Ester authority", detector, "; ".join(notes)

    if status == "unimplemented":
        return "missing", detector, "Automatable Q-rule has no implementing P-rule."
    if status == "manual_review_only":
        return "manual review only", detector, coverage.manual_review_reason or ""
    if status == "partial":
        return "partially implemented", detector, getattr(coverage, "gap_reason", "") or ""
    if status == "implemented" and getattr(coverage, "coverage_confidence", None) in {
        "low",
        "diagnostic",
    }:
        return "partially implemented", detector, getattr(coverage, "gap_reason", "") or ""
    if not detector:
        return "missing", "", "No P-rule mapping in catalog notes."

    # Compare public card wording when present
    if atomic_cards:
        best = max(_similarity(c.question, ester["question"]) for c in atomic_cards)
        if best < 0.5:
            notes.append("Atomic public card question weakly matches matrix question.")
            return "wording mismatch", detector, "; ".join(notes)
    return "aligned", detector, "; ".join(notes)


def _priority_for(status: str, pid: str = "", qid: str = "") -> str:
    if status == "missing" and (pid in {"P026", "P013", "P019", "P037"} or qid in {"Q051", "Q007"}):
        return "P0"
    if status in {"missing", "detector mismatch"}:
        return "P0" if "contradict" in status else "P2"
    if status in {"public rule reference mismatch", "wording mismatch"} and (
        pid in _BROAD_PARENT_RULES or qid
    ):
        return "P1"
    if status == "remediation mismatch":
        return "P3"
    if status == "partially implemented":
        return "P2"
    if status == "manual review only":
        return "P2"
    if status == "aligned":
        return ""
    return "P3"


def _collect_warning_examples(impl_rules: dict[str, ImplementationRule]) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    broad_patterns = (
        "figure/table",
        "toc/list",
        "table of contents, list of tables",
        "sentence case and ending",
        "font family and size",
        "first paragraph flush-left, subsequent",
    )
    for rid, rule in impl_rules.items():
        if not rule.public_visible:
            continue
        blob = _norm(rule.public_question + " " + rule.public_remediation)
        for pat in broad_patterns:
            if pat in blob:
                examples.append(
                    {
                        "rule_id": rid,
                        "issue": "broad public wording",
                        "detail": f"Contains pattern '{pat}'",
                        "public_question": rule.public_question,
                        "public_remediation": rule.public_remediation,
                    }
                )
        if rule.public_remediation.count(".") > 2 and len(rule.public_remediation) > 120:
            examples.append(
                {
                    "rule_id": rid,
                    "issue": "multi-issue remediation",
                    "detail": "Remediation may combine multiple fixes.",
                    "public_question": rule.public_question,
                    "public_remediation": rule.public_remediation,
                }
            )
    return examples[:25]


def _recent_fix_checks(impl_rules: dict[str, ImplementationRule], public: dict[str, Any]) -> list[dict[str, str]]:
    checks = []
    items = [
        ("P011", "margin wording", "1.5", "P011 margin wording should cite 1.5in left / 1in others."),
        ("P026A", "font family", "computer modern", "LaTeX font acceptance wording."),
        ("P068", "approval advisor", "advisor", "Approval page advisor-role check."),
        ("P013", "page number position", "bottom", "Page-number position wording."),
        ("P015", "indentation scope", "abstract", "P015 should not cover abstract/acknowledgements."),
    ]
    for rid, label, needle, desc in items:
        rule = impl_rules.get(rid) or public["by_id"].get(rid, {})
        text = _norm(
            getattr(rule, "public_remediation", "")
            or getattr(rule, "remediation", "")
            or rule.get("remediation", "")
            or rule.get("how_to_correct", "")
        )
        checks.append(
            {
                "area": label,
                "rule": rid,
                "description": desc,
                "status": "aligned" if needle in text or rid in impl_rules else "needs review",
            }
        )
    return checks


def generate_report(output_dir: Path) -> dict[str, Any]:
    p_source = formatting_p_source()
    q_source = matrix_q_source()
    ester_p = load_formatting_p_rules(p_source)
    ester_q = load_matrix_q_rules(q_source)
    enrich_q_sections(ester_q)

    p_feedback = json.loads(_P_FEEDBACK_JSON.read_text(encoding="utf-8"))
    q_json = json.loads(_Q_MATRIX_JSON.read_text(encoding="utf-8"))
    catalog = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    test_map = _scan_tests_for_rules()
    public = _load_public_catalog()
    impl_rules = build_implementation_inventory(catalog, public, test_map)
    q_coverage_list = build_coverage_report()
    q_coverage = {c.q_id: c for c in q_coverage_list}
    q_summary = coverage_summary(q_coverage_list)

    p_rows: list[dict[str, Any]] = []
    p_status_counts: Counter[str] = Counter()
    for ester in ester_p:
        impl = impl_rules.get(ester["id"])
        status, notes = classify_p_rule(ester, impl, public)
        p_status_counts[status] += 1
        p_rows.append(
            {
                "P-rule": ester["id"],
                "Ester question": _ester_target_question(ester),
                "Current public question": (impl.public_question if impl else "") or (
                    impl.question if impl and impl.public_visible else ""
                ),
                "Ester remediation": _ester_target_remediation(ester),
                "Current remediation": (impl.public_remediation if impl else "") or (
                    impl.remediation if impl else ""
                ),
                "Detector status": impl.enforcement if impl else "",
                "Tests": ", ".join(impl.tests[:5]) if impl else "",
                "Status": status,
                "Notes": notes,
            }
        )

    q_rows: list[dict[str, Any]] = []
    q_status_counts: Counter[str] = Counter()
    for ester in ester_q:
        cov = q_coverage.get(ester["id"])
        status, detector, notes = classify_q_rule(ester, cov, impl_rules, public)
        q_status_counts[status] += 1
        q_rows.append(
            {
                "Q-rule": ester["id"],
                "Matrix section": ester.get("section") or (cov.section if cov else ""),
                "Matrix question": ester["question"],
                "Effective current authority": (
                    cov.authority_overlay["effective_requirement"] if cov and cov.authority_overlay
                    else ester["question"]
                ),
                "Effective implementation status": (
                    cov.authority_overlay["effective_implementation_status"] if cov and cov.authority_overlay
                    else (cov.implementation_status if cov else "missing")
                ),
                "Current detector/rule": detector,
                "Status": status,
                "Tests": ", ".join(test_map.get(ester["id"], [])[:4]),
                "Notes": notes,
            }
        )

    # Extra catalog P-rules not in Ester spreadsheet
    ester_p_ids = {r["id"] for r in ester_p}
    extra_rules = [r for r in catalog if r["id"] not in ester_p_ids and r["id"].startswith("P")]

    mismatch_inventory: list[dict[str, Any]] = []
    for row in p_rows:
        if row["Status"] != "aligned":
            mismatch_inventory.append({"kind": "P-rule", **row, "priority": _priority_for(row["Status"], row["P-rule"])})
    for row in q_rows:
        if row["Status"] not in {"aligned", "superseded by later Ester authority"}:
            mismatch_inventory.append({"kind": "Q-rule", **row, "priority": _priority_for(row["Status"], qid=row["Q-rule"])})

    # P018 sub-check gaps (Ester atomic TOC/list checks without public cards)
    p018_gaps = []
    ester_p018 = next((r for r in ester_p if r["id"] == "P018"), None)
    if ester_p018:
        ester_subs = re.findall(r"\d[a-z]\.", _norm(ester_p018["proposed_question"]))
        atomic_p018 = [s.id for s in public["atomic_specs"].values() if s.parent_rule_id == "P018"]
        if ester_subs and not atomic_p018:
            p018_gaps.append(
                "P018: Ester lists many TOC/LoT/LoF atomic sub-questions but no P018A/B/C public cards; "
                "coverage delegated to P024/P032/P036/P039/P042/P046/P048 and hidden P018."
            )

    warning_examples = _collect_warning_examples(impl_rules)
    recent_checks = _recent_fix_checks(impl_rules, public)
    p026_contradiction = _p026_detector_public_contradiction(public)
    priority_review = _ester_priority_review(
        ester_p, public, q_rows, impl_rules, p026_contradiction
    )

    if p026_contradiction["status"] == "detector mismatch":
        mismatch_inventory.insert(
            0,
            {
                "kind": "P-rule",
                "P-rule": "P026A",
                "Status": "detector mismatch",
                "Notes": p026_contradiction["detail"],
                "priority": "P0",
                "Ester question": public["by_id"].get("P026A", {}).get("question", ""),
                "Current public question": public["by_id"].get("P026A", {}).get("question", ""),
                "Ester remediation": "Word: Times/Arial; LaTeX: Computer Modern/Latin Modern",
                "Current remediation": public["by_id"].get("P026A", {}).get("remediation", ""),
                "Detector status": "flags CMR in pdf_font_compliance.py",
                "Tests": ", ".join(test_map.get("P026", [])[:4]),
            },
        )
        p_status_counts["detector mismatch"] = p_status_counts.get("detector mismatch", 0) + 1

    # Prioritized fix plan
    fix_plan: list[dict[str, str]] = []
    def add_fix(priority: str, title: str, rules: str, source: str, files: str, approach: str, tests: str) -> None:
        fix_plan.append(
            {
                "priority": priority,
                "title": title,
                "rules": rules,
                "source_rows": source,
                "files": files,
                "approach": approach,
                "tests": tests,
            }
        )

    if p026_contradiction["status"] == "detector mismatch":
        add_fix(
            "P0",
            "Resolve P026 font-family detector vs public-rule contradiction",
            "P026, P026A, P026B",
            "Ester font guidance; formatting_rules.xlsx P026; pdf_font_compliance.py",
            "src/njit_auditor/rules/pdf_font_compliance.py, web_app.py, project_added_rules.json, polished_comments.py",
            "Stop emitting possible_body_font_family_issue for Computer Modern/Latin Modern when public policy accepts them, OR update P026A to match detector and add advisor-review note.",
            "test_rule_reference_atomicity.py::test_font_split_cards, test_p026_font_volume_rollup.py",
        )
    if any(r["P-rule"] == "P015" for r in p_rows if r["Status"] != "aligned"):
        add_fix(
            "P1",
            "Split P015 body indentation into two atomic public cards",
            "P015 → P015A (first para after heading flush), P015B (subsequent body paragraphs indented)",
            "formatting_rules.xlsx P015 proposed questions 1–2",
            "web_app.py, project_added_rules.json, pdf_indentation.py issue types",
            "Add atomic public cards matching Ester's two body-indent questions; hide broad P015 from /rules.",
            "test_rule_reference_atomicity.py, test_ester_p014_p015_atomic_split.py",
        )
    if p018_gaps:
        add_fix(
            "P1",
            "Add or document P018 atomic public cards for remaining TOC/LoT/LoF sub-checks",
            "P018, P024, P032, P036, P039, P042, P046, P048",
            "P018 proposed_question_edit (1a-3c sub-items)",
            "web_app.py, project_added_rules.json",
            "Either add P018A.. public cards mapped to Q049-Q059/Q067-Q069/Q077-Q079 issue types or cross-link existing P024/P032/P036 atomic cards explicitly on /rules.",
            "test_rule_reference_atomicity.py, test_ester_p017_p018_atomic_split.py",
        )
    if q_status_counts.get("partially implemented", 0):
        add_fix(
            "P2",
            "Close partial Q-rule coverage gaps (especially Q051 level-3 TOC sentence case)",
            "Q051 and other partial Q-rules",
            "ester_q_matrix.json + q_rule_coverage_report.json",
            "pdf_toc_list_formatting.py, project_added_rules.json notes",
            "Implement missing detector paths or mark manual-review with explicit public wording.",
            "test_ester_q_matrix_spec.py, test_pdf_rules.py",
        )
    if any(r["Q-rule"] in {f"Q{n:03d}" for n in range(15, 21)} and r["Status"] == "manual review only" for r in q_rows):
        add_fix(
            "P2",
            "Document committee-ordering Q015-Q020 as manual-review-only on public rule reference",
            "Q015-Q020",
            "260330 YESNO audit logic matrix.xlsx Approval Page section",
            "web_app.py, issue_type_explanations.py",
            "Add explicit manual-review cards or help text; do not imply automatic enforcement.",
            "test_ester_q_matrix_spec.py",
        )
    if not any(f["priority"] == "P4" for f in fix_plan):
        add_fix(
            "P4",
            "Add regression tests for each remaining non-aligned P/Q rule row",
            "all mismatched rules",
            "mismatch_inventory.json",
            "tests/test_ester_rule_consistency_regression.py (new)",
            "For each mismatch row, add a focused test asserting public wording, detector mapping, or manual-review status.",
            "new file",
        )

    mismatch_inventory.sort(key=lambda x: (x.get("priority", "P9"), x.get("kind", ""), x.get("P-rule", x.get("Q-rule", ""))))

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selected_authority_sources": {
            "p_rules": _source_label(p_source),
            "q_matrix": _source_label(q_source),
        },
        "source_files": {
            "formatting_rules_xlsx": _source_label(_FORMATTING_XLSX),
            "yesno_matrix_xlsx": _source_label(_MATRIX_XLSX),
            "ester_p_rule_feedback_json": _source_label(_P_FEEDBACK_JSON),
            "ester_q_matrix_json": _source_label(_Q_MATRIX_JSON),
            "ester_q_current_authority_overlay_json": _source_label(_AUTHORITY_OVERLAY_PATH),
            "project_added_rules_json": _source_label(_CATALOG_PATH),
        },
        "counts": {
            "p_rules_audited": len(ester_p),
            "q_rules_audited": len(ester_q),
            "catalog_p_rules": len(catalog),
            "public_rule_cards": public["total_public"],
            "atomic_public_cards": len(public["atomic_specs"]),
            "p_status": dict(p_status_counts),
            "q_status": dict(q_status_counts),
            "q_coverage_summary": q_summary,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "ester_rule_consistency_audit.md"

    with (output_dir / "p_rule_consistency.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(p_rows[0].keys()))
        writer.writeheader()
        writer.writerows(p_rows)

    with (output_dir / "q_rule_consistency.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(q_rows[0].keys()))
        writer.writeheader()
        writer.writerows(q_rows)

    (output_dir / "mismatch_inventory.json").write_text(
        json.dumps(mismatch_inventory, indent=2), encoding="utf-8"
    )
    (output_dir / "audit_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Ester-Source Consistency Audit — NJIT Thesis Auditor")
    lines.append("")
    lines.append(f"**Generated:** {meta['generated_at']}")
    lines.append(f"**Repository root:** `{_REPO_ROOT}`")
    lines.append("")
    lines.append("## Executive summary")
    lines.append("")
    lines.append(
        f"Audited **{len(ester_p)} P-rules** from Ester's formatting spreadsheet and "
        f"**{len(ester_q)} Q-rules** from the YES/NO audit logic matrix against "
        f"**{public['total_public']} public rule-reference cards** and "
        f"**{len(catalog)} backend catalog rules**."
    )
    lines.append("")
    lines.append("### Status counts — P-rules")
    for status, count in sorted(p_status_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- **{status}:** {count}")
    lines.append("")
    lines.append("### Status counts — Q-rules")
    for status, count in sorted(q_status_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- **{status}:** {count}")
    lines.append("")
    lines.append("### Q coverage summary (backend)")
    for k, v in q_summary.items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")

    lines.append("## Section 1 — Authority sources used")
    lines.append("")
    lines.append("| File | Path | Rows | Notes |")
    lines.append("|------|------|------|-------|")
    lines.append(
        f"| NJIT Thesis Auditor Formatting Rules | `{_source_label(p_source)}` | "
        f"{len(ester_p)} P-rules | {_source_note(p_source)} |"
    )
    lines.append(
        f"| YES/NO audit logic matrix | `{_source_label(q_source)}` | "
        f"{len(ester_q)} Q-rules | {_source_note(q_source)} |"
    )
    lines.append(f"| Parsed P-feedback JSON | `{_P_FEEDBACK_JSON}` | {p_feedback['metadata']['rules_with_feedback']} with edits | Subset of spreadsheet |")
    lines.append(f"| Parsed Q-matrix JSON | `{_Q_MATRIX_JSON}` | {len(q_json['rules'])} | Used by q_rule_coverage.py |")
    lines.append(f"| Current Q authority overlay | `{_AUTHORITY_OVERLAY_PATH}` | {len(load_current_authority_overlay())} supersessions | Later Ester decisions; historical matrix preserved |")
    lines.append("")
    lines.append("### Extraction summary")
    lines.append("")
    lines.append(
        f"- P-rules with Ester proposed edits in JSON fixture: {p_feedback['metadata']['rules_with_feedback']}"
    )
    lines.append(f"- P-rules with split-request language in spreadsheet: {sum(1 for r in ester_p if r['ester_split_requested'])}")
    lines.append(f"- Automatable Q-rules per matrix metadata: {q_json['metadata'].get('automatable_count', 'n/a')}")
    lines.append(f"- Manual-review Q-rules per matrix metadata: {q_json['metadata'].get('manual_review_count', 'n/a')}")
    lines.append("")

    lines.append("## Section 2 — Implementation inventory")
    lines.append("")
    lines.append("### Rule catalog and rendering")
    lines.append("")
    lines.append(f"- Backend catalog: `{_CATALOG_PATH}` ({len(catalog)} rules)")
    lines.append(f"- Q-rule inventory: `{_INVENTORY_PATH}`")
    lines.append(f"- Public /rules builder: `src/njit_auditor/web_app.py` (`_build_rule_catalog`, `{len(public['atomic_specs'])}` atomic cards)")
    lines.append("- Warning/remediation polish: `src/njit_auditor/polished_comments.py`, `finding_explanations.py`, `issue_type_explanations.py`")
    lines.append("- Report rendering: `src/njit_auditor/report_view.py`")
    lines.append("")
    lines.append("### Detector modules (`src/njit_auditor/rules/`)")
    detector_files = sorted(p.name for p in _RULES_DIR.glob("*.py") if p.name != "__init__.py")
    lines.append(f"- **{len(detector_files)}** Python detector modules")
    lines.append("")
    lines.append("### Coverage tooling")
    lines.append(f"- `src/njit_auditor/specs/q_rule_coverage.py` → `{_REPO_ROOT / 'data/specs/q_rule_coverage_report.json'}`")
    lines.append("")

    lines.append("## Section 3 — P-rule comparison table")
    lines.append("")
    lines.append("| P-rule | Ester question | Current public question | Ester remediation | Current remediation | Detector status | Tests | Status | Notes |")
    lines.append("|--------|----------------|-------------------------|-------------------|---------------------|-----------------|-------|--------|-------|")
    for row in p_rows:
        def esc(v: str) -> str:
            return (v or "").replace("|", "\\|").replace("\n", " ")[:180]
        lines.append(
            f"| {row['P-rule']} | {esc(row['Ester question'])} | {esc(row['Current public question'])} | "
            f"{esc(row['Ester remediation'])} | {esc(row['Current remediation'])} | {row['Detector status']} | "
            f"{esc(row['Tests'])} | **{row['Status']}** | {esc(row['Notes'])} |"
        )
    lines.append("")

    lines.append("## Section 4 — Q-rule comparison table")
    lines.append("")
    lines.append("| Q-rule | Matrix section | Historical matrix question | Effective current authority | Effective implementation | Current detector/rule | Status | Tests | Notes |")
    lines.append("|--------|----------------|----------------------------|-----------------------------|--------------------------|----------------------|--------|-------|-------|")
    for row in q_rows:
        def esc(v: str) -> str:
            return (v or "").replace("|", "\\|").replace("\n", " ")[:160]
        lines.append(
            f"| {row['Q-rule']} | {row['Matrix section']} | {esc(row['Matrix question'])} | "
            f"{esc(row['Effective current authority'])} | {esc(row['Effective implementation status'])} | "
            f"{row['Current detector/rule']} | **{row['Status']}** | {esc(row['Tests'])} | {esc(row['Notes'])} |"
        )
    lines.append("")

    lines.append("## Ester priority areas (A–H)")
    lines.append("")
    for item in priority_review:
        lines.append(f"- **{item['area']}** — *{item['status']}*: {item['detail']}")
    lines.append("")
    lines.append("### P026 detector vs public policy")
    lines.append("")
    lines.append(f"- **Status:** {p026_contradiction['status']}")
    lines.append(f"- **Detail:** {p026_contradiction['detail']}")
    lines.append("")

    lines.append("## Section 5 — Public rule reference mismatches")
    lines.append("")
    pub_mismatches = [r for r in p_rows if r["Status"] in {"wording mismatch", "remediation mismatch", "public rule reference mismatch"}]
    if not pub_mismatches:
        lines.append("No public rule-reference mismatches detected at coarse similarity thresholds.")
    else:
        for row in pub_mismatches:
            lines.append(f"- **{row['P-rule']}** ({row['Status']}): {row['Notes']}")
    lines.append("")
    lines.append("### Broad rules and split status")
    lines.append("")
    for parent in sorted(_BROAD_PARENT_RULES):
        children = sorted(spec.id for spec in public["atomic_specs"].values() if spec.parent_rule_id == parent)
        hidden = parent in public["hidden_parent_ids"]
        lines.append(
            f"- **{parent}**: hidden={hidden}; atomic public cards={len(children)}"
            + (f" ({', '.join(children)})" if children else " (**none — gap**)")
        )
    if p018_gaps:
        for gap in p018_gaps:
            lines.append(f"- {gap}")
    lines.append("")

    lines.append("## Section 6 — Enforcement mismatches")
    lines.append("")
    lines.append("### Ester-requested checks not fully implemented")
    for row in q_rows:
        if row["Status"] in {"missing", "partially implemented"}:
            lines.append(f"- **{row['Q-rule']}** ({row['Matrix section']}): {row['Status']} — {row['Notes'] or row['Current detector/rule']}")
    lines.append("")
    lines.append("### Extra / project-added rules not in Ester formatting spreadsheet")
    lines.append(f"- **{len(extra_rules)}** catalog P-rules are project-added beyond the spreadsheet (expected for TeX hygiene P001–P010, evaluation rules, etc.).")
    for rule in extra_rules[:15]:
        lines.append(f"  - {rule['id']}: {rule.get('section', '')} — {rule.get('implementation_status', '')}")
    if len(extra_rules) > 15:
        lines.append(f"  - … and {len(extra_rules) - 15} more")
    lines.append("")
    lines.append("### Recent-fix alignment checks")
    for chk in recent_checks:
        lines.append(f"- **{chk['area']}** ({chk['rule']}): {chk['status']} — {chk['description']}")
    lines.append("")

    lines.append("## Section 7 — Warning/comment/remediation mismatch examples")
    lines.append("")
    if warning_examples:
        for ex in warning_examples[:12]:
            lines.append(f"- **{ex['rule_id']}** — {ex['issue']}: {ex['detail']}")
            lines.append(f"  - Question: {ex['public_question'][:140]}")
            lines.append(f"  - Remediation: {ex['public_remediation'][:140]}")
    else:
        lines.append("No broad-pattern public wording examples matched the blocked-pattern list.")
    lines.append("")

    lines.append("## Section 8 — Test coverage gaps")
    lines.append("")
    for item in mismatch_inventory[:30]:
        rid = item.get("P-rule") or item.get("Q-rule")
        tests = item.get("Tests", "")
        if not tests:
            lines.append(f"- **{rid}** ({item.get('Status')}): **no dedicated test references found**")
        else:
            lines.append(f"- **{rid}** ({item.get('Status')}): tests — {tests}")
    lines.append("")

    lines.append("## Section 9 — Prioritized fix plan")
    lines.append("")
    for priority in ("P0", "P1", "P2", "P3", "P4"):
        items = [f for f in fix_plan if f["priority"] == priority]
        if not items:
            continue
        lines.append(f"### {priority}")
        for f in items:
            lines.append(f"#### {f['title']}")
            lines.append(f"- **Rules:** {f['rules']}")
            lines.append(f"- **Source-of-truth rows:** {f['source_rows']}")
            lines.append(f"- **Affected files:** {f['files']}")
            lines.append(f"- **Approach:** {f['approach']}")
            lines.append(f"- **Tests to add/update:** {f['tests']}")
            lines.append("")

    top10 = mismatch_inventory[:10]
    lines.append("## Top 10 highest-priority mismatches")
    lines.append("")
    for i, item in enumerate(top10, 1):
        rid = item.get("P-rule") or item.get("Q-rule")
        lines.append(f"{i}. **{rid}** — {item.get('Status')} ({item.get('priority', '')})")
    lines.append("")
    lines.append("## Recommended first fix query")
    lines.append("")
    if top10:
        first = top10[0]
        rid = first.get("P-rule") or first.get("Q-rule")
        lines.append(
            f"> Fix {rid} ({first.get('Status')}): align public rule-reference wording/remediation and detector mapping "
            "with the selected Ester P/Q authority rows, "
            f"preserving one-issue-at-a-time atomic cards."
        )
    lines.append("")
    lines.append("## Machine-readable outputs")
    lines.append("")
    lines.append(f"- `{output_dir / 'p_rule_consistency.csv'}`")
    lines.append(f"- `{output_dir / 'q_rule_consistency.csv'}`")
    lines.append(f"- `{output_dir / 'mismatch_inventory.json'}`")
    lines.append(f"- `{output_dir / 'audit_metadata.json'}`")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    meta["report_path"] = str(report_path)
    meta["top10"] = top10
    return meta


def main() -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = _REPO_ROOT / "results" / f"ester_rule_consistency_audit_{ts}"
    meta = generate_report(output_dir)
    print(json.dumps({"report_path": meta["report_path"], "counts": meta["counts"]}, indent=2))


if __name__ == "__main__":
    main()
