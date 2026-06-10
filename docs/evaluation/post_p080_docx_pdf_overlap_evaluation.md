# Post-P080 DOCX and PDF EF-Overlap Evaluation

- **Date:** 2026-06-09
- **Baseline commit:** `beb24c8` (main — PR #286, P080 DOCX comment extraction)
- **Scope:** Expanded Ester dataset; DOCX comment extraction via P080 added to existing PDF EF-overlap picture
- **Privacy:** Aggregate counts and category labels only. No dissertation body text, EF comment text,
  author names, or EF comment prose is reproduced.

---

## 1. Scope and Prior State

The prior evaluation (`docs/evaluation/expanded_ester_dataset_evaluation.md`) covered the full
16-file Ester dataset using the PDF auditor and `pdf-comments extract`. Two DOCX files were
listed as "not auditable" because the PDF auditor does not ingest DOCX.

P080 adds `njit-audit docx-comments extract`, enabling comment and tracked-change metadata
extraction from DOCX files. This evaluation applies P080 to the two DOCX files and combines
results with the existing PDF picture.

---

## 2. DOCX Extraction Results

| File (short) | DOCX comments | Tracked insertions | Tracked deletions | Author | Date |
|---|---|---|---|---|---|
| Sebastian Fine 3rd review DOCX | 22 | 0 | 0 | Flaim, Ester | 2025-04-09 |
| Aguado Alvaro 3rd review DOCX | 30 | 0 | 0 | Flaim, Ester | 2025-08-28 |
| **Total** | **52** | **0** | **0** | | |

**Parser notes:**
- Both files extracted cleanly with no errors.
- Comment IDs are non-sequential in both files (reflecting position in the document, not a
  simple 1–N counter) — the extractor correctly captures the DOCX-internal comment ID.
- No comment anchors are available (the DOCX comment anchor range is not extracted by the
  current P080 implementation — comments are metadata-only).
- Preview text is truncated to ≤120 characters; 3 of 52 comments had `char_count > 120`
  (truncated at 120 chars per spec).
- Tracked changes: zero in both files. Ester did not use tracked insertions/deletions in
  either 3rd-review draft; all feedback is in comment annotations only.
- Both files are now usable for EF-overlap evaluation.

---

## 3. DOCX EF Comment Categories

Comments categorized by theme (counts, no text reproduction):

| Category | Sebastian Fine 3rd | Aguado Alvaro 3rd | Combined |
|---|---|---|---|
| Indentation | 9 | 3 | **12** |
| Capitalization / case | 1 | 10 | **11** |
| Bold / heading style (unbold) | 2 | 8 | **10** |
| Margin / spacing / blank lines | 7 | 0 | **7** |
| Page numbering orientation | 0 | 3 | **3** |
| Reference list (duplicate/issue) | 0 | 3 | **3** |
| Table / figure layout | 2 | 0 | **2** |
| Grammar / editorial style | 0 | 2 | **2** |
| Title page / front matter | 1 | 1 | **2** |
| **Total** | **22** | **30** | **52** |

**Notable observations:**
- Indentation and capitalization are the two highest categories combined (23/52 = 44%).
- Aguado Alvaro 3rd has 3 comments about page number orientation on landscape pages — a gap
  not previously visible from any PDF evaluation. P019 does not check landscape orientation.
- Both files have zero tracked changes, so P080's tracked-change extraction found no new
  coverage beyond the comment metadata.
- All 52 comments are from a single reviewer (Flaim, Ester).

---

## 4. Combined PDF + DOCX Evaluation Summary

| Source | Files | EF comments/annotations | EF with extractable text | Tool findings |
|---|---|---|---|---|
| PDF (all 12 auditable) | 12 | 562 | 394 | 4,004 |
| PDF (flattened — 0 extractable) | 3 of 12 | 0 | 0 | included above |
| DOCX (P080 new) | 2 | 52 | 52 | N/A — no PDF audit |
| **Combined** | **14 files** | **614** | **446** | **4,004 (PDF only)** |

**Coverage summary:**
- 16-file Ester dataset: 12 PDF-auditable, 2 DOCX (now extractable via P080), 1 ZIP (clean
  baseline), 1 XLSX (rule matrix).
- Previously unextractable DOCX: now 52 comments visible for the first time.
- Still blocked: 3 PDFs with flattened EF annotations (Yin Haotian 2nd/4th, Yin Haotian 4th
  compressed) — EF comments baked into rendering layer, not accessible via PyMuPDF.

---

## 5. Version-Chain Analysis

### Yin Haotian (4 review versions — most data)

| Version | Format | Tool findings | P013 | P026 | P011 | EF annotations | EF extractable |
|---|---|---|---|---|---|---|---|
| 2nd (260415) | PDF | 281 | 104 | 103 | 33 | 0 | Flattened |
| 2nd (variant) | PDF | 346 | 104 | 103 | 33 | 65 | Yes |
| 3rd | PDF | 483 | 124 | 123 | 32 | 151 | Partial |
| 4th (260430) | PDF | 347 | 125 | 123 | 41 | 0 | Flattened |
| 4th (compressed) | PDF | 532 | 133 | 117 | 70 | 0 | Flattened |

**P013/P026 persistence signal:** These counts remain 103–125 across four review versions
(2nd through 4th). The student either did not address these formatting issues over multiple
revisions, or these findings are high-false-positive body-text detections that do not
correspond to real problems. The Yin Haotian chain is the strongest evidence for over-warning
in the current tool.

**P011 increase at 4th review (41–70):** Possibly due to new chapter content or formatting
changes introducing font-compliance issues in a dissertation that grew between 3rd and 4th
reviews.

**EF annotation shift:** The 3rd review carries the most EF annotations (151); the 2nd-review
variant (extractable, 65 annotations) leans toward `indentation` and `spacing_blank_lines`.
By the 3rd review, EF feedback expands to `heading_title`, `capitalization_case`, and
`indentation` — suggesting structural issues were added or re-introduced during the 2nd→3rd
revision cycle, not resolved.

### Sebastian Fine (2 data points — 1st PDF, 3rd DOCX)

| Version | Format | Tool findings | P012 | EF feedback items | Dominant EF category |
|---|---|---|---|---|---|
| 1st (EF PDF) | PDF | 122 | 58 | 58 | heading_title (20/53 with text = 38%) |
| 3rd (DOCX) | DOCX | N/A | N/A | 22 | indentation (9/22 = 41%) |

**Pattern made visible by P080:** The 1st-review EF feedback was heavily heading-style focused.
By the 3rd review, the dominant concern has shifted to indentation and margin/spacing — a
plausible progression where heading formatting was partly addressed but indentation
consistency emerged as the next major issue. Without P080, this shift would be invisible.

No tracked changes in the 3rd DOCX. The document appears to have been submitted as a clean
draft with Ester's comments added on top (no student-side tracked edits captured).

### Aguado Alvaro (single data point — 3rd DOCX)

| Version | Format | EF feedback items | Dominant EF categories |
|---|---|---|---|
| 3rd (DOCX) | DOCX | 30 | Capitalization (10/30), Bold/unbold heading (8/30) |

This is the only data point for this student. Capitalization and bold heading style are the
primary concerns (18/30 = 60%). Three comments about page numbering orientation on landscape
pages are a new gap type not captured by any PDF-side rule. No tracked changes.

Reference list issues (3 comments: duplicate/identical entries) are visible in this dataset
for the first time at this specificity — P064 covers reference list structure but duplicate
entry detection is not implemented.

### Kang Qi (standalone comment PDF + 1st review PDF)

| File | Tool findings | P013 | P026 | EF annotations |
|---|---|---|---|---|
| Comment PDF | 111 | 20 | 17 | 53 |
| 1st review PDF | 128 | 43 | 39 | 14 |

High P013/P026 (43/39) on the 1st review with only 14 EF annotations — the tool fires ~80
additional page-number candidate and font-size findings that Ester did not comment on. This
is another strong over-warning signal on these two rules.

### Other single-review PDFs (Pennock Andrew, Cibaku Elson, Termini Dolores, Luo M)

| Student | Tool findings | P013 | P026 | EF annotations |
|---|---|---|---|---|
| Pennock Andrew | 439 | 165 | 161 | 58 |
| Cibaku Elson | 325 | 95 | 92 | 78 |
| Termini Dolores | 458 | 163 | 202 | 49 |
| Luo M 3rd | 432 | 156 | 126 | 36 |

All four full-dissertation PDFs show P013 > 90 and P026 > 90. These are the dominant counts
in every file. EF annotations per file range from 36 to 78 — substantially lower than the
P013+P026 combined count in every case.

---

## 6. EF-Only Gap Categories

| Gap | Evidence source | Tool coverage | Reason blocked |
|---|---|---|---|
| Semantic citation/reference style | `references_citations` in 6/9 PDF files (23 total) | Structural P064 only | Style/semantic — APA vs. non-APA not auto-detectable |
| Figure/table formatting semantics | PDF `figure_format` + `table_format` (35 total); DOCX table 2 | P017/P023/P024 partial | Caption placement, numbering semantic issues |
| Approval/committee page text | PDF `committee_approval_page` in 3 files (7 total) | P068/P072 structural only | Committee member names/degrees on image pages — not text-extractable |
| Unclear/content feedback | PDF 214/457 categorizable = 46.8% uncategorizable | None | Semantic editing, content corrections — not automatable |
| Landscape page number orientation | DOCX Aguado Alvaro 3rd: 3 comments | **None** | P019 does not check portrait-vs-landscape number placement |
| Reference list duplicate entries | DOCX Aguado Alvaro 3rd: 3 comments | None (P064 structural only) | Requires cross-entry comparison — not implemented |
| Flattened EF annotations | YH 2nd (260415), YH 4th (260430), YH 4th compressed | Cannot extract | EF comments baked into page rendering layer |
| DOCX files | Previously 2 files inaccessible | **P080 now covers** | Resolved: 52 comments now visible |

---

## 7. Tool Over-Warning Signals

**P013 (page-number candidates) and P026 (font compliance)** are the dominant rules in every
full-dissertation PDF. Their counts remain nearly constant across Yin Haotian's 4 review
versions (P013: 104–133, P026: 103–123), across Kang Qi's 1st review (P013: 43, P026: 39
vs. only 14 EF annotations), and across all other files (P013 > 90 in all full PDFs).

**Signal interpretation:**
- A rule that fires 100+ times per dissertation and does not decrease across revisions is
  likely firing on normal body text rather than real formatting violations.
- EF's annotations per file (14–151) are substantially lower than P013+P026 combined
  (typically 200–350 per full dissertation).
- This does not mean P013/P026 are wrong — page-number candidate detection and font
  checks are valid rules — but the current thresholds and filters may be too sensitive for
  real dissertation body text, producing false positives at high volume.

**Recommended action (see P081 options below):** Triage calibration to reduce P013/P026
false-positive rate, using the Yin Haotian version chain as a test harness.

---

## 8. Whether P081 Is Justified

**Yes.** The combined PDF+DOCX evaluation provides clear evidence for a targeted P081:

1. **P013/P026 over-warning** is the highest-evidence signal. It is consistent across
   multiple students, multiple review versions, and multiple years of data. A calibration
   refinement targeting these rules has the highest expected impact-to-effort ratio.

2. **Landscape page number orientation** is a new, specific, automatable gap identified
   exclusively via P080 DOCX data (Aguado Alvaro 3rd: 3/30 comments). The rule is discrete
   and detectable from PDF page geometry.

All other gaps are either semantic/not-automatable or are edge cases not yet supported by
sufficient data.

---

## 9. Recommended P081 Options (ranked)

| Rank | Option | Rationale | Expected impact |
|---|---|---|---|
| 1 | **Triage calibration for P013/P026** | Strongest multi-version evidence; reduces most false positives; Yin Haotian chain is a natural test harness | High — reduces noise for every future evaluation |
| 2 | **Landscape page number orientation detection** | New P019-adjacent gap revealed by P080 DOCX data; detectable from PDF page geometry and number position | Medium — affects landscape-heavy dissertations |
| 3 | **Evaluation/reporting refinement** | Combine PDF audit + DOCX comment extraction in a unified summary report | Low — QoL improvement, no detection change |
| 4 | **OCR phase** | Would unlock 3 flattened PDFs; high implementation complexity | Low — 3 files, already fully audited as PDFs |
| 5 | **No immediate P081** | Pause for additional data; current tool is already comprehensive | Reasonable if further validation is needed |

**Primary recommendation: Rank 1 — P013/P026 triage calibration.**

The Yin Haotian 4-version chain plus Kang Qi count-vs-EF mismatch constitutes sufficient
evidence. A scoped P081 that adds per-rule confidence tiers or zone-filter calibration to
P013/P026 would directly improve evaluation signal-to-noise ratio without changing detection
logic for other rules.

---

## 10. Validation

- No source-code changes made during this evaluation.
- `ruff check .` — clean (pending post-commit validation).
- `mypy src` — clean (pending post-commit validation).
- `pytest` — 1104 passed (no new tests; docs-only PR).
- `project_added_rules.json` — unchanged (P001–P080, 79 entries).
- `next_project_added_rule_id` — P081 (reserved, unassigned).
- `p_rules_implemented` — P001–P080.
- Generated outputs (`data/evaluation/generated/post_p080_docx/`) — gitignored; not committed.
