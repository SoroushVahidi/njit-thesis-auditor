# Atomic Rule Split Plan — Ester's YES/NO Audit Logic Matrix
Based on feedback from Ester's review of the NJIT Thesis Auditor.
Source: YES/NO Audit Logic Matrix (Q001–Q079), June 2026.

This document tracks broad P-rules that Ester says should be split into atomic
binary checks matching the YES/NO matrix, with corresponding Q-rule references.

---

## PR 1 (Current): Wording / Remediation Pass
Branch: `ux/ester-rule-wording-pass1`

Changes already made:
- P011: strict margin question and remediation (1.5 in left, 1 in top/bottom/right)
- P012: remediation → "Resolve or delete all annotations"
- P013: question and remediation → bottom-center placement
- P016: question and remediation → text flow with exception for necessary page breaks
- P020: remediation → check source document, not PDF extraction
- P026: remediation → Word/LaTeX paths, Computer Modern is accepted equivalent
- P038: remediation → clarify canonical ACKNOWLEDGEMENTS spelling

---

## PR 2: Split P014 into Atomic Front-Matter Heading Checks

**Current rule:** P014 — "Do named front-matter headings follow expected layout/style heuristics?"
Single heuristic checking bold/centered/top/all-caps for named headings.

**Ester's mapping to YES/NO matrix:**

| Q-Rule | Check | Target Page |
|--------|-------|-------------|
| Q001 | Abstract page free of visible page number | Abstract |
| Q008 | Title Page free of visible page number | Title Page |
| Q009 | Copyright page has no header text in top margin | Copyright |
| Q013 | Approval Page heading "APPROVAL PAGE" all caps, bold, centered, top | Approval |
| Q021 | Biographical Sketch heading "BIOGRAPHICAL SKETCH" all caps, bold, centered, top | Bio Sketch |
| Q032 | Dedication page has no header text in top margin | Dedication |
| Q036 | Acknowledgements heading "ACKNOWLEDGEMENTS" all caps, bold, centered, top | Acknowledgements |
| Q047 | TOC heading "TABLE OF CONTENTS" all caps, bold, centered, top | TOC |
| Q048 | TOC continuation pages show "TABLE OF CONTENTS (Continued)" | TOC continuation |
| Q061 | List of Tables heading "LIST OF TABLES" all caps, bold, centered | List of Tables |
| Q062 | List of Tables continuation pages show "LIST OF TABLES (Continued)" | LoT continuation |
| Q063 | "Table" label bold, left-aligned under LoT heading | List of Tables |
| Q064 | "Page" label bold, right-aligned under LoT heading | List of Tables |
| Q070 | List of Figures heading "LIST OF FIGURES" all caps, bold, centered | List of Figures |
| Q071 | List of Figures continuation pages show "LIST OF FIGURES (Continued)" | LoF continuation |
| Q072 | "Figure" label bold, left-aligned under LoF heading | List of Figures |
| Q073 | "Page" label bold, right-aligned under LoF heading | List of Figures |

**Implementation plan:**
- Keep P014 as a broad heuristic pass for unlisted heading pages
- Add separate P-rules or sub-checks for each Q-rule above
- Q009/Q032 overlap with P034/P041 (margin header text) — consolidate

---

## PR 2: Split P015 into Atomic Indentation Checks

**Current rule:** P015 — "Do front-matter/body paragraphs show likely indentation issues?"
Single rule for all paragraph types.

**Ester's mapping:**

| Q-Rule | Check | Section |
|--------|-------|---------|
| Q002 | First Abstract paragraph flush-left (no indent) | Abstract |
| Q003 | Subsequent Abstract paragraphs have first-line indent | Abstract |
| Q044 | First Acknowledgements paragraph flush-left | Acknowledgements |
| Q045 | Subsequent Acknowledgements paragraphs have first-line indent | Acknowledgements |

**Implementation plan:**
- P015 already checks `unexpected_opening_indent` (Q002/Q044) and `missing_later_indent` (Q003/Q045)
- The existing per-section dispatch (Abstract vs. Acknowledgements) exists in `pdf_abstract_indentation.py` and `pdf_acknowledgements_indentation.py`
- PR 2 should add separate atomic rule IDs for each section's checks rather than routing everything through P015

---

## PR 3: Split P017 into Atomic Caption/Title Checks

**Current rule:** P017 — "Do figure/table caption and title lines show obvious formatting issues?"
Covers all caption/title formatting.

**Ester's atomic checks:**

| Check | Type | Rule |
|-------|------|------|
| Figure captions use sentence case | Figure | New |
| Figure captions end with terminal period | Figure | Partial in P017 |
| Figure captions single-spaced/justified | Figure | New |
| Figure label "Figure N." is bold | Figure | New |
| Table titles use title case (no terminal period) | Table | New |
| Table title has no final period | Table | Partial in P017 |
| Multi-line table title is single-spaced | Table | New |

**Implementation plan:**
- Split `pdf_captions.py` into figure-specific and table-specific checks
- Add styling checks for bold Figure label and single-spacing

---

## PR 3: Split P018 into Atomic TOC/LoT/LoF Alignment Checks

**Current rule:** P018 — "Do TOC/List of Tables/List of Figures entries show likely alignment inconsistencies?"
Combined alignment rule.

**Ester's atomic checks:**

### TOC (Q049–Q059):
- Q049: Level-1 TOC entries in ALL CAPS
- Q050: Level-2 TOC entries in Title Case
- Q051: Level-3 TOC entries in Sentence Case
- Q052: Consistent leader style (dots/hyphens) for all entries
- Q053/Q054/Q055: Wrapped entries single-spaced (per level)
- Q056: Level-2 and Level-3 entries indented relative to parent
- Q057: Double spacing between consecutive TOC section entries
- Q058/Q059: Single vs. multiple appendix labeling

### List of Tables (Q065–Q069):
- Q065: Table titles in title case, no final period
- Q066: Wrapped table titles single-spaced
- Q067: Double spacing between entries
- Q068: Table numbers aligned in left column
- Q069: Page numbers aligned in right column

### List of Figures (Q074–Q079):
- Q074: Figure descriptions in sentence case
- Q075: Figure descriptions have terminal punctuation
- Q076: Wrapped figure descriptions single-spaced
- Q077: Double spacing between entries
- Q078: Figure numbers aligned in left column
- Q079: Page numbers aligned in right column

**Implementation plan:**
- Split P018 into P018a (TOC), P018b (LoT), P018c (LoF) or use sub-checks with separate issue_types
- Many of these checks are already partially implemented in P024 (capitalization), P036 (spacing), P039 (indentation)
- Cross-reference existing rules before adding new detectors

---

## PR 4: P026 Accepted Font Policy Decision

**Current behavior:** Computer Modern (CMR) is flagged as non-Times.
**Ester's guidance:** Word users → Times New Roman; LaTeX/Overleaf users → Computer Modern is accepted.

**Decision needed:**
- Option A: Add CMR to the accepted font list in `pdf_font_compliance.py` (no more flags for LaTeX)
- Option B: Keep flagging CMR but add a note in remediation (current PR 1 approach)
- Option C: Detect document source (Word vs. LaTeX) and apply different font policies

**Recommendation:** Option A after confirming with NJIT policy. The remediation already says "verify with advisor" as a bridge.

---

## PR 5: Q-Rules Not Yet Implemented

The following Ester matrix questions have no corresponding P-rule:

### Acknowledgements content (Q037–Q043):
| Q-Rule | Check |
|--------|-------|
| Q037 | First paragraph explicitly thanks advisor(s) |
| Q038 | Second paragraph explicitly thanks committee members |
| Q039 | Third paragraph mentions both technical and financial support |
| Q040 | Grant support includes full agency name and grant number |
| Q041 | Fifth paragraph mentions peers, colleagues, or students |
| Q042 | Sixth paragraph (if present) mentions family or friends |
| Q043 | Named persons use full first and last name |

### Approval Page ordering (Q015–Q020):
- Q015: Committee entries begin with honorific
- Q016: Dissertation Advisor appears before non-advisor entries
- Q017: Committee members in descending rank order
- Q018: Same-rank members alphabetized by surname
- Q019: External (non-NJIT) entries appear after NJIT entries
- Q020: External entries include institution, city, and state

**Note:** These content checks require NLP/semantic analysis and are high-effort to implement reliably from PDF text extraction.
