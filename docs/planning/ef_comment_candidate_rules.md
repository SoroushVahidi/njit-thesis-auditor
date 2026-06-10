# EF-Comment Candidate Rules Register

- **Date:** 2026-06-10
- **Status:** no candidates currently qualify under the five-gate evidence policy
- **Source:** P083 gap register (`data/processed/ef_comment_coverage.json`)
- **Policy:** `docs/planning/p083_ef_comment_coverage_taxonomy_scope_and_design.md`

---

## Five-gate evidence policy (summary)

A structural gap may become a future detector only if it passes all five gates:

1. **Guideline reference** — backed by explicit NJIT guideline (Q-rule or spec section).
2. **Multi-document occurrence** — at least 3 dissertation files show the pattern.
3. **Heuristic detectability** — detectable from PDF text-layer metadata alone.
4. **False-positive estimate** — ≤1 false positive in 5 clean-baseline checks.
5. **Actionability** — student can fix without re-reading their entire dissertation.

---

## Gap register

### GAP-1: Heading bold/weight enforcement

| Field | Value |
|---|---|
| SMI count | 10 (2 DOCX_3RD_A + 8 DOCX_3RD_B) |
| Category | `bold_heading_style` |
| Description | Reviewer directed removing bold from specific headings or heading levels |
| Closest existing rule | P027 (heading level style consistency) |
| Gate 1 (Guideline) | UNCERTAIN — no explicit NJIT spec section mandating non-bold at specific heading levels found |
| Gate 2 (Multi-document) | **FAIL** — only 2 DOCX files show the pattern; minimum 3 required |
| Gate 3 (Detectability) | PARTIAL — bold weight is detectable from `span.bold`/font-name heuristics |
| Gate 4 (False-positive) | NOT EVALUATED (blocked at gate 2) |
| Gate 5 (Actionability) | LIKELY — reviewer comment targets specific heading levels |
| **Verdict** | **BLOCKED** — gate 2 fails; revisit if ≥1 more file shows this pattern |

---

### GAP-2: Reference list duplicate / per-entry formatting

| Field | Value |
|---|---|
| SBL count | 3 (DOCX_3RD_B) |
| Category | `reference_list_issue` |
| Description | Reviewer flagged duplicate entries or per-entry formatting inconsistencies |
| Closest existing rule | P064 (reference-list structural checks) |
| Gate 1 (Guideline) | YES — duplicate references are a formatting error |
| Gate 2 (Multi-document) | UNKNOWN (only 2 DOCX files available) |
| Gate 3 (Detectability) | **FAIL** — duplicate detection requires comparing reference string content; per-entry formatting requires parsing citation format semantics — both exceed heuristic layout scope |
| Gate 4 (False-positive) | NOT EVALUATED (blocked at gate 3) |
| Gate 5 (Actionability) | YES |
| **Verdict** | **BLOCKED** — gate 3 fails; semantic content parsing required; not feasible for heuristic auditor |

---

### GAP-3: LOT/LOF/TOC zero coverage on comparison PDFs

| Field | Value |
|---|---|
| SMI count | 4 (comparison PDF category estimate, not in DOCX coverage table) |
| Category | `list_of_tables_figures_toc` |
| Description | Reviewer comments on LoT/LoF/TOC structure on Cibaku/Yin Haotian comparison PDFs |
| Closest existing rule | P036 (TOC/LoF/LoT entry spacing), P037 (roman numeral pages) |
| Gate 1 (Guideline) | PARTIAL — LoT/LoF formatting is in NJIT spec |
| Gate 2 (Multi-document) | UNCERTAIN — only 4 comments across 2 comparison PDFs |
| Gate 3 (Detectability) | PARTIAL — structural TOC/list checks are in scope but 0 findings on comparison PDFs suggests existing rules already check what's detectable |
| Gate 4 (False-positive) | NOT EVALUATED |
| Gate 5 (Actionability) | LIKELY |
| **Verdict** | **BLOCKED** — insufficient document count; not individually annotated (category-level estimate only); revisit with more annotated PDFs |

---

## Summary

| Gap | SMI/SBL | Blocking gate | Revisit condition |
|---|---|---|---|
| Heading bold/weight enforcement | 10 SMI | Gate 2 (document count) | ≥1 more dissertation file showing the same pattern |
| Reference list duplicate/formatting | 3 SBL | Gate 3 (detectability) | Never (semantic content required) |
| LoT/LoF/TOC comparison-PDF gap | 4 SMI (estimated) | Gate 2 (document count) | ≥3 individually annotated files showing the pattern |

**Current conclusion:** no new detector candidates qualify. The auditor's heuristic coverage
is at its natural ceiling for the currently available annotated data. Future progress requires
either (a) more annotated dissertation files, or (b) reclassifying a blocked gap as tractable
after NJIT guideline clarification.
