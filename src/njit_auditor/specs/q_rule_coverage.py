"""Q-rule coverage audit: maps Q001-Q079 to implementing P-rules.

Reads the Ester Q-matrix spec and the project_added_rules catalog, then
produces a coverage report showing which Q-rules are:
  - implemented  : at least one P-rule detector covers the check
  - manual_review: not automatable by PDF heuristics (NLP/template-matching required)
  - unimplemented: automatable but no P-rule covers it yet
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_SPECS_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "specs"
_RULES_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "processed" / "rules"

# Resolve relative to this file's repo location robustly.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_Q_MATRIX_PATH = _REPO_ROOT / "data" / "specs" / "ester_q_matrix.json"
_CATALOG_PATH = _REPO_ROOT / "data" / "processed" / "rules" / "project_added_rules.json"


@dataclass
class QRuleCoverage:
    q_id: str
    section: str
    question: str
    automatable: bool
    implementation_status: str  # 'implemented', 'manual_review_only', 'unimplemented'
    coverage_confidence: str = ""
    manual_review_reason: str = ""
    implementing_p_rules: list[str] = field(default_factory=list)


def _expand_q_range(text: str) -> set[str]:
    """Expand 'Q053-Q055' and 'Q053,Q055,Q066-Q067' into individual Q-IDs."""
    ids: set[str] = set()
    # Plain Q-refs
    for m in re.finditer(r"Q(\d+)-Q(\d+)", text):
        start, end = int(m.group(1)), int(m.group(2))
        for n in range(start, end + 1):
            ids.add(f"Q{n:03d}")
    # Remove range spans so remaining Q-refs aren't double-counted
    cleaned = re.sub(r"Q\d+-Q\d+", "", text)
    for m in re.finditer(r"Q(\d+)", cleaned):
        ids.add(f"Q{int(m.group(1)):03d}")
    return ids


def _load_q_matrix() -> list[dict]:
    data = json.loads(_Q_MATRIX_PATH.read_text(encoding="utf-8"))
    return data["rules"]


def _load_catalog() -> list[dict]:
    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return data


_STRUCTURED_Q_FIELDS = ("source_q_rule_ids", "q_rule_ids")
_Q_ID_RE = re.compile(r"Q\d{3}")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
# A notes sentence that says a Q-rule is NOT covered by this rule.
_NEGATIVE_NOTE_RE = re.compile(
    r"manual[- ]only|\bnot\b|n't\b|\bremoved\b|\bno longer\b|\bsuperseded\b"
    r"|\bexcluded\b|\bout of scope\b|\bdeferred\b",
    re.IGNORECASE,
)
_P_RULE_REF_RE = re.compile(r"\bP(\d{3})")


def _structured_q_ids(rule: dict) -> set[str] | None:
    """Return the rule's structured Q-IDs, or None when it declares none.

    A present field is authoritative even when empty. Malformed values raise
    ValueError naming the rule instead of silently skewing coverage.
    """
    present = [name for name in _STRUCTURED_Q_FIELDS if name in rule]
    if not present:
        return None
    ids: set[str] = set()
    for name in present:
        value = rule[name]
        if not isinstance(value, list) or not all(
            isinstance(item, str) and _Q_ID_RE.fullmatch(item) for item in value
        ):
            raise ValueError(
                f"{rule.get('id', '?')}: {name} must be a list of Q-IDs like 'Q052', "
                f"got {value!r}"
            )
        ids.update(value)
    return ids


def _note_q_ids(rule_id: str, notes: str) -> set[str]:
    """Legacy fallback: Q-IDs a rule's notes positively claim for that rule.

    Older catalog records state their Q basis only in prose ("heuristic for
    Q056"). A sentence is ignored when it negates coverage ("Q015-Q020
    remain manual-only", "not checked", "was removed") or credits another
    P-rule ("P044 handles Q002/Q003", "via P032").
    """
    ids: set[str] = set()
    for sentence in _SENTENCE_SPLIT_RE.split(notes):
        if _NEGATIVE_NOTE_RE.search(sentence):
            continue
        if any(f"P{num}" != rule_id for num in _P_RULE_REF_RE.findall(sentence)):
            continue
        ids |= _expand_q_range(sentence)
    return ids


def _build_q_to_p_map(catalog: list[dict]) -> dict[str, list[str]]:
    """Return {Q-ID: [P-rule-IDs]}.

    Structured ``source_q_rule_ids``/``q_rule_ids`` are authoritative; notes
    are consulted only for records that declare neither field.
    """
    q_to_p: dict[str, list[str]] = {}
    for rule in catalog:
        pid = rule.get("id", "")
        if not pid.startswith("P"):
            continue
        structured = _structured_q_ids(rule)
        if structured is not None:
            q_ids = structured
        else:
            q_ids = _note_q_ids(pid, str(rule.get("notes", "")))
        for qid in q_ids:
            q_to_p.setdefault(qid, []).append(pid)
    return q_to_p


def build_coverage_report() -> list[QRuleCoverage]:
    """Return a per-Q-rule coverage record for all Q001-Q079."""
    q_rules = _load_q_matrix()
    catalog = _load_catalog()
    q_to_p = _build_q_to_p_map(catalog)

    results: list[QRuleCoverage] = []
    for rule in q_rules:
        qid = rule["id"]
        # Normalize to zero-padded form for lookup
        m = re.match(r"Q(\d+)$", qid)
        if not m:
            continue
        padded = f"Q{int(m.group(1)):03d}"
        implementing = sorted(set(q_to_p.get(padded, [])))
        automatable = rule.get("automatable", True)

        if not automatable:
            status = "manual_review_only"
            coverage = "medium"
        elif implementing:
            status = "implemented"
            coverage = "medium"
        else:
            status = "unimplemented"
            coverage = "low"

        results.append(QRuleCoverage(
            q_id=qid,
            section=rule.get("section", ""),
            question=rule.get("question", ""),
            automatable=automatable,
            implementation_status=status,
            coverage_confidence=coverage,
            manual_review_reason=rule.get("manual_review_reason", ""),
            implementing_p_rules=implementing,
        ))

    return results


def coverage_summary(report: list[QRuleCoverage]) -> dict[str, int]:
    implemented = sum(1 for r in report if r.implementation_status == "implemented")
    manual = sum(1 for r in report if r.implementation_status == "manual_review_only")
    unimplemented = sum(1 for r in report if r.implementation_status == "unimplemented")
    return {
        "total": len(report),
        "implemented": implemented,
        "manual_review_only": manual,
        "unimplemented": unimplemented,
    }


REPORT_PATH = _REPO_ROOT / "data" / "specs" / "q_rule_coverage_report.json"


def coverage_report_payload(report: list[QRuleCoverage], generated: str) -> dict[str, object]:
    """Return the checked-in ``q_rule_coverage_report.json`` structure.

    Deterministic for a given catalog, Q-matrix and *generated* date: rows
    follow Q-matrix order and implementing rules are sorted.
    """
    return {
        "generated": generated,
        "summary": coverage_summary(report),
        "q_rules": [
            {
                "q_id": r.q_id,
                "section": r.section,
                "question": r.question,
                "implementation_status": r.implementation_status,
                "implementing_p_rules": list(r.implementing_p_rules),
                "manual_review_reason": r.manual_review_reason,
            }
            for r in report
        ],
    }


def render_coverage_report(generated: str) -> str:
    """Serialize the current coverage report in the checked-in file's format."""
    payload = coverage_report_payload(build_coverage_report(), generated)
    return json.dumps(payload, indent=2)


def main(argv: list[str] | None = None) -> int:
    """Regenerate ``data/specs/q_rule_coverage_report.json``.

    Usage: ``python -m njit_auditor.specs.q_rule_coverage [--generated YYYY-MM-DD]
    [--output PATH]``. The date defaults to today.
    """
    import argparse
    import datetime

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--generated", default=datetime.date.today().isoformat())
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    args.output.write_text(render_coverage_report(args.generated), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
