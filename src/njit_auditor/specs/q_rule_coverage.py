"""Q-rule coverage audit: maps Q001-Q079 to implementing P-rules.

Reads the Ester Q-matrix spec and the project_added_rules catalog, then
produces a coverage report showing which Q-rules are:
  - implemented        : a P-rule actively detects this check (high or medium confidence)
  - partial            : a P-rule is referenced but coverage is explicit-gap or diagnostic-only
  - manual_review_only : not automatable by PDF heuristics
  - unimplemented      : automatable but no P-rule references it at all

Coverage confidence tiers
--------------------------
high          A P-rule directly targets this Q-rule as its primary check.
medium        A P-rule partially covers this Q-rule alongside others.
low           A P-rule mentions this Q-rule in notes but its own notes also
              say the check is not performed or remains manual-only.
diagnostic    The only matching P-rules are infrastructure/diagnostic rules
              that emit no standalone findings.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_Q_MATRIX_PATH = _REPO_ROOT / "data" / "specs" / "ester_q_matrix.json"
_CATALOG_PATH = _REPO_ROOT / "data" / "processed" / "rules" / "project_added_rules.json"

# P-rules that reference Q-rules in notes but are broad page-presence or
# infrastructure rules; they emit no standalone findings for the specific check.
# When one of these is the *only* P-rule for a Q-rule, confidence is "diagnostic".
_DIAGNOSTIC_P_RULES = frozenset({"P018", "P071", "P072"})

# Phrases in P-rule notes that mean the named Q-rule is explicitly not checked.
_NOT_CHECKED_PHRASES = [
    "not checked",
    "remains manual-only",
    "remain manual-only",
    "no standalone findings",
    "does not emit standalone findings",
]

# Verb phrases that — immediately following a Q-ID chain — mean those Q-IDs are not checked.
_EXCL_VERB = (
    r"(?:is|are)\s+not\s+checked",
    r"remains?\s+manual[- ]only",
    r"(?:is|are)\s+manual[- ]only",
    r"(?:is|are)\s+not\s+implemented",
)
_EXCL_VERB_JOINED = "(?:" + "|".join(_EXCL_VERB) + ")"

# Match: chain of "Q### (optional annotation) [and]" followed by exclusion verb.
# Captures all Q-IDs in the leading chain via findall on the captured prefix.
_CHAIN_EXCL_RE = re.compile(
    r"((?:Q\d+(?:\s+\([^)]+\))?\s*(?:,\s*|\band\b\s*)?)+?)\s*" + _EXCL_VERB_JOINED,
    re.IGNORECASE,
)
# Regex: "Q015-Q020 remain manual-only"
_RANGE_EXCL_RE = re.compile(
    r"Q(\d+)-Q(\d+)\s+remain[s]?\s+manual[- ]only",
    re.IGNORECASE,
)


def _extract_explicit_exclusions(notes: str) -> set[str]:
    """Return Q-IDs explicitly stated as not checked / manual-only in a notes string."""
    excluded: set[str] = set()
    # Range patterns: "Q015-Q020 remain manual-only"
    for m in _RANGE_EXCL_RE.finditer(notes):
        for n in range(int(m.group(1)), int(m.group(2)) + 1):
            excluded.add(f"Q{n:03d}")
    # Chain patterns: "Q023 (…) and Q024 (…) are manual-only"
    for m in _CHAIN_EXCL_RE.finditer(notes):
        chain_text = m.group(1)
        for qm in re.finditer(r"Q(\d+)", chain_text):
            excluded.add(f"Q{int(qm.group(1)):03d}")
    return excluded


def _expand_q_range(text: str) -> set[str]:
    """Expand 'Q053-Q055' and bare 'Q053,Q055,Q066-Q067' into individual Q-IDs."""
    ids: set[str] = set()
    for m in re.finditer(r"Q(\d+)-Q(\d+)", text):
        for n in range(int(m.group(1)), int(m.group(2)) + 1):
            ids.add(f"Q{n:03d}")
    cleaned = re.sub(r"Q\d+-Q\d+", "", text)
    for m in re.finditer(r"Q(\d+)", cleaned):
        ids.add(f"Q{int(m.group(1)):03d}")
    return ids


def _load_q_matrix() -> list[dict]:
    data = json.loads(_Q_MATRIX_PATH.read_text(encoding="utf-8"))
    return data["rules"]


def _load_catalog() -> list[dict]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _build_q_maps(
    catalog: list[dict],
) -> tuple[dict[str, list[str]], set[str]]:
    """Return ({Q-ID: [P-rule-IDs]}, {Q-IDs explicitly excluded in notes})."""
    q_to_p: dict[str, list[str]] = {}
    globally_excluded: set[str] = set()

    for rule in catalog:
        pid = rule.get("id", "")
        if not pid.startswith("P"):
            continue
        notes = rule.get("notes", "") or ""
        q_ids_field = rule.get("q_rule_ids", [])
        q_ids_str = " ".join(q_ids_field) if isinstance(q_ids_field, list) else ""
        combined = " ".join([notes, q_ids_str])

        # Q-IDs explicitly stated as not implemented in this P-rule's notes.
        excl = _extract_explicit_exclusions(notes)
        globally_excluded |= excl

        for qid in _expand_q_range(combined):
            q_to_p.setdefault(qid, []).append(pid)

    return q_to_p, globally_excluded


@dataclass
class QRuleCoverage:
    q_id: str
    section: str
    question: str
    automatable: bool
    # Status: 'implemented', 'partial', 'manual_review_only', 'unimplemented'
    implementation_status: str
    # Confidence: 'high', 'medium', 'low', 'diagnostic', ''
    coverage_confidence: str = ""
    manual_review_reason: str = ""
    implementing_p_rules: list[str] = field(default_factory=list)
    # Human-readable explanation of any coverage gap
    gap_reason: str = ""


def _confidence(
    q_id: str,
    implementing: list[str],
    globally_excluded: set[str],
) -> tuple[str, str]:
    """Return (confidence, gap_reason) for an implemented Q-rule."""
    if q_id in globally_excluded:
        return "low", (
            f"{q_id} is referenced in P-rule notes but explicitly stated as not checked "
            f"or remaining manual-only in those same notes ({', '.join(implementing)})."
        )
    active = [p for p in implementing if p not in _DIAGNOSTIC_P_RULES]
    if not active:
        return "diagnostic", (
            f"{q_id} is referenced only by infrastructure/diagnostic P-rules "
            f"({', '.join(implementing)}) that emit no standalone findings."
        )
    return "medium", ""


def build_coverage_report() -> list[QRuleCoverage]:
    """Return a per-Q-rule coverage record for all Q001-Q079."""
    q_rules = _load_q_matrix()
    catalog = _load_catalog()
    q_to_p, globally_excluded = _build_q_maps(catalog)

    results: list[QRuleCoverage] = []
    for rule in q_rules:
        qid = rule["id"]
        m = re.match(r"Q(\d+)$", qid)
        if not m:
            continue
        padded = f"Q{int(m.group(1)):03d}"
        implementing = sorted(set(q_to_p.get(padded, [])))
        automatable = rule.get("automatable", True)

        if not automatable:
            results.append(QRuleCoverage(
                q_id=qid,
                section=rule.get("section", ""),
                question=rule.get("question", ""),
                automatable=False,
                implementation_status="manual_review_only",
                manual_review_reason=rule.get("manual_review_reason", ""),
                implementing_p_rules=implementing,
            ))
            continue

        if not implementing:
            results.append(QRuleCoverage(
                q_id=qid,
                section=rule.get("section", ""),
                question=rule.get("question", ""),
                automatable=True,
                implementation_status="unimplemented",
                implementing_p_rules=[],
                gap_reason=f"{qid} has no P-rule referencing it.",
            ))
            continue

        confidence, gap_reason = _confidence(padded, implementing, globally_excluded)
        if confidence in ("low", "diagnostic"):
            status = "partial"
        else:
            status = "implemented"

        results.append(QRuleCoverage(
            q_id=qid,
            section=rule.get("section", ""),
            question=rule.get("question", ""),
            automatable=True,
            implementation_status=status,
            coverage_confidence=confidence,
            implementing_p_rules=implementing,
            gap_reason=gap_reason,
        ))

    return results


def coverage_summary(report: list[QRuleCoverage]) -> dict[str, int]:
    implemented = sum(1 for r in report if r.implementation_status == "implemented")
    partial = sum(1 for r in report if r.implementation_status == "partial")
    manual = sum(1 for r in report if r.implementation_status == "manual_review_only")
    unimplemented = sum(1 for r in report if r.implementation_status == "unimplemented")
    return {
        "total": len(report),
        "implemented": implemented,
        "partial": partial,
        "manual_review_only": manual,
        "unimplemented": unimplemented,
    }
