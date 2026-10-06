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


def _build_q_to_p_map(catalog: list[dict]) -> dict[str, list[str]]:
    """Return {Q-ID: [P-rule-IDs]} from catalog notes/q_rule_ids/source_q_rule_ids fields."""
    q_to_p: dict[str, list[str]] = {}
    for rule in catalog:
        pid = rule.get("id", "")
        if not pid.startswith("P"):
            continue
        # Keep legacy note-based mappings while also honoring structured source_q_rule_ids.
        source_q_ids = rule.get("source_q_rule_ids", [])
        q_ids_field = rule.get("q_rule_ids", [])
        q_ids_str = " ".join(q_ids_field) if isinstance(q_ids_field, list) else str(q_ids_field)
        source_q_str = (
            " ".join(source_q_ids) if isinstance(source_q_ids, list) else str(source_q_ids)
        )
        combined = " ".join([str(rule.get("notes", "")), q_ids_str, source_q_str])
        for qid in _expand_q_range(combined):
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
