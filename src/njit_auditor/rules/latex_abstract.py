"""Abstract-oriented checks for LaTeX source projects."""

from __future__ import annotations

import re

from njit_auditor.latex_loader import LoadedTexProject, TeXSourceFile
from njit_auditor.latex_text import strip_latex_to_text
from njit_auditor.models import AuditFinding, Severity

FORBIDDEN_WORD_RE = re.compile(r"\b(paper|papers|article|articles)\b", re.IGNORECASE)
FIRST_PERSON_RE = re.compile(r"\b(i|me|my|mine|we|us|our|ours)\b", re.IGNORECASE)
ABSTRACT_BLOCK_RE = re.compile(
    r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
    re.IGNORECASE | re.DOTALL,
)

# Degree-type detection patterns (scanned across source files)
_PHD_RE = re.compile(
    r"\b(ph\.?d|doctor\w*|doctoral|dissertation)\b", re.IGNORECASE
)
_MS_RE = re.compile(
    r"\b(master\w*|m\.?s\.?|m\.?eng\.?|thesis)\b", re.IGNORECASE
)

PHD_WORD_LIMIT = 350
MS_WORD_LIMIT = 150


def count_abstract_words(plain_text: str) -> int:
    """Count words conservatively: sequences that contain at least one letter."""
    return sum(1 for tok in plain_text.split() if re.search(r"[a-zA-Z]", tok))


def infer_degree_type(project: LoadedTexProject) -> str:
    """
    Return 'phd', 'ms', or 'unknown' by scanning source files for degree indicators.

    PhD signals: 'dissertation', 'doctoral', 'Ph.D', 'Doctor'.
    MS signals: 'thesis', 'master', 'M.S.', 'M.Eng'.
    'dissertation' takes precedence over 'thesis' since the former is PhD-specific at NJIT.
    """
    phd_score = 0
    ms_score = 0
    for source_file in project.files:
        text = source_file.text
        phd_score += len(_PHD_RE.findall(text))
        ms_score += len(_MS_RE.findall(text))

    # 'dissertation' is PhD-specific; weight it above 'thesis'
    if phd_score > 0 and phd_score >= ms_score:
        return "phd"
    if ms_score > 0 and ms_score > phd_score:
        return "ms"
    return "unknown"


def _iter_abstract_sources(project: LoadedTexProject) -> list[tuple[TeXSourceFile, str]]:
    sources: list[tuple[TeXSourceFile, str]] = []
    for source_file in project.files:
        blocks = [m.group(1) for m in ABSTRACT_BLOCK_RE.finditer(source_file.text)]
        if blocks:
            sources.append((source_file, "\n".join(blocks)))
            continue
        if "abstract" in source_file.path.name.lower():
            sources.append((source_file, source_file.text))
    return sources


def run_latex_abstract_checks(project: LoadedTexProject) -> list[AuditFinding]:
    """Run forbidden-term and first-person checks on abstract content."""

    findings: list[AuditFinding] = []
    abstract_sources = _iter_abstract_sources(project)
    if not abstract_sources:
        return [
            AuditFinding(
                rule_id="P008",
                severity=Severity.WARNING,
                message="No abstract block/file detected in TeX sources.",
                details={"suggested_fix": "Add a \\begin{abstract}...\\end{abstract} section."},
            )
        ]

    for source_file, text in abstract_sources:
        plain_text = strip_latex_to_text(text)
        forbidden_terms = sorted(
            {m.group(1).lower() for m in FORBIDDEN_WORD_RE.finditer(plain_text)}
        )
        for term in forbidden_terms:
            findings.append(
                AuditFinding(
                    rule_id="Q004",
                    severity=Severity.FAIL,
                    message=(
                        f"Abstract uses forbidden term '{term}' "
                        "(paper/article variants are not allowed)."
                    ),
                    details={
                        "file": str(source_file.path),
                        "line": str(_approx_line_number(text, term)),
                        "suggested_fix": "Replace with dissertation/study/work/research wording.",
                    },
                )
            )
        pronouns = sorted({m.group(1).lower() for m in FIRST_PERSON_RE.finditer(plain_text)})
        for pronoun in pronouns:
            findings.append(
                AuditFinding(
                    rule_id="Q005",
                    severity=Severity.FAIL,
                    message=f"First-person pronoun '{pronoun}' detected in abstract.",
                    details={
                        "file": str(source_file.path),
                        "line": str(_approx_line_number(text, pronoun)),
                        "suggested_fix": "Rewrite sentence in neutral third-person style.",
                    },
                )
            )

    if not findings:
        return [
            AuditFinding(
                rule_id="Q004",
                severity=Severity.PASS,
                message="Abstract forbidden-term and first-person checks passed.",
            )
        ]
    return findings


def _approx_line_number(raw_text: str, token: str) -> int:
    """Find an approximate line number for a detected token in raw source text."""

    token_re = re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE)
    for idx, line in enumerate(raw_text.splitlines(), start=1):
        if token_re.search(line):
            return idx
    return 1


def run_latex_abstract_word_count_check(project: LoadedTexProject) -> list[AuditFinding]:
    """Check abstract word count against NJIT PhD/MS limits (P021).

    PhD limit: 350 words. MS limit: 150 words.
    Degree type is inferred from source text; defaults to 350 when unknown.
    Word count is conservative: only tokens containing at least one letter.
    """
    abstract_sources = _iter_abstract_sources(project)
    if not abstract_sources:
        return []

    degree = infer_degree_type(project)
    if degree == "phd":
        limit = PHD_WORD_LIMIT
    elif degree == "ms":
        limit = MS_WORD_LIMIT
    else:
        limit = PHD_WORD_LIMIT  # conservative default: higher limit

    findings: list[AuditFinding] = []
    for source_file, raw_text in abstract_sources:
        plain = strip_latex_to_text(raw_text)
        word_count = count_abstract_words(plain)

        if degree == "unknown":
            if word_count <= MS_WORD_LIMIT:
                # Within both limits — no issue
                continue
            # Over MS limit; may or may not exceed PhD limit
            severity = Severity.WARNING
            if word_count > PHD_WORD_LIMIT:
                msg = (
                    f"Abstract word count ({word_count}) exceeds the PhD limit of "
                    f"{PHD_WORD_LIMIT} words. Degree type could not be determined."
                )
                confidence = "high"
            else:
                msg = (
                    f"Abstract word count ({word_count}) may exceed the MS limit of "
                    f"{MS_WORD_LIMIT} words. Degree type could not be determined from source."
                )
                confidence = "low"
        elif word_count > limit:
            severity = Severity.WARNING
            degree_label = "PhD" if degree == "phd" else "MS"
            msg = (
                f"Abstract word count ({word_count}) exceeds the {degree_label} limit of "
                f"{limit} words."
            )
            confidence = "medium"
        else:
            continue  # within limit — no finding

        findings.append(
            AuditFinding(
                rule_id="P021",
                severity=severity,
                message=msg,
                details={
                    "file": str(source_file.path),
                    "word_count": str(word_count),
                    "limit": str(limit),
                    "inferred_degree_type": degree,
                    "confidence": confidence,
                },
            )
        )

    return findings
