# Atomic Rule Split Plan — Ester's YES/NO Audit Logic Matrix
Based on feedback from Ester's review of the NJIT Thesis Auditor.
Source: YES/NO Audit Logic Matrix (Q001–Q079), June 2026.
Formatting Rules Spreadsheet: `results/ester_feedback_raw/formatting_rules.xlsx`

This document tracks broad P-rules that Ester says should be split into atomic
binary checks matching the YES/NO matrix, with corresponding Q-rule references.

---

## PR 1 (Done): Wording / Remediation Pass — `ux/ester-rule-wording-pass1`

Changes made in Pass 1 and Pass 2 of this branch:

| P-Rule | Change |
|--------|--------|
| P011 | Strict margin question/remediation: 1.5 in left, 1 in top/bottom/right; no content in margins |
| P012 | Remediation: "Resolve or delete all annotations before final submission" |
| P013 | Question and remediation → bottom-center placement, 0.5 inches from bottom edge |
| P016 | Pass 1: remediation with necessary page-break exception. Pass 2: question aligned with Ester exact wording |
| P020 | Remediation: always check source document (Word or Overleaf) not PDF text extraction |
| P026 | Remediation: Word/Overleaf dual-path; Computer Modern is accepted equivalent |
| P038 | Remediation: clarifies canonical ACKNOWLEDGEMENTS spelling (double-E) |

---

## PR 2: Split P014 into Atomic Front-Matter Heading Checks

**Current rule:** P014 — "Do named front-matter headings follow expected layout/style heuristics?"
Single heuristic checking bold/centered/top/all-caps for named headings.

**Ester's mapping to YES/NO matrix:**

| Q-Rule | Check | Target Page | Overlap with existing P-rule? |
|--------|-------|-------------|-------------------------------|
| Q001 | Abstract page free of visible page number | Abstract | P022 already covers this |
| Q008 | Title Page free of visible page number | Title Page | P022 already covers this |
| Q009 | Copyright page has no header text in top margin | Copyright | P034 already covers this |
| Q013 | Approval Page heading "APPROVAL PAGE" all caps, bold, centered, top | Approval | P038 covers phrase; P014 split for format |
| Q021 | Biographical Sketch heading "BIOGRAPHICAL SKETCH" all caps, bold, centered, top | Bio Sketch | P038 covers phrase; P014 split for format |
| Q032 | Dedication page has no header text in top margin | Dedication | P041 already covers this |
| Q036 | Acknowledgements heading "ACKNOWLEDGEMENTS" all caps, bold, centered, top | Acknowledgements | P038 covers phrase; P014 split for format |
| Q047 | TOC heading "TABLE OF CONTENTS" all caps, bold, centered, top | TOC | P038 covers phrase; P014 split for format |
| Q048 | TOC continuation pages show "TABLE OF CONTENTS (Continued)" | TOC continuation | P030 already covers this |
| Q061 | List of Tables heading "LIST OF TABLES" all caps, bold, centered | List of Tables | P038 covers phrase; P014 split for format |
| Q062 | List of Tables continuation pages show "LIST OF TABLES (Continued)" | LoT continuation | P030 already covers this |
| Q063 | "Table" label bold, left-aligned under LoT heading | List of Tables | P031 already covers this |
| Q064 | "Page" label bold, right-aligned under LoT heading | List of Tables | P031 already covers this |
| Q070 | List of Figures heading "LIST OF FIGURES" all caps, bold, centered | List of Figures | P038 covers phrase; P014 split for format |
| Q071 | List of Figures continuation pages show "LIST OF FIGURES (Continued)" | LoF continuation | P030 already covers this |
| Q072 | "Figure" label bold, left-aligned under LoF heading | List of Figures | P031 already covers this |
| Q073 | "Page" label bold, right-aligned under LoF heading | List of Figures | P031 already covers this |

**Implementation plan:**
- Q001, Q008, Q012, Q014 (no visible page number) → already covered by P022; no new detector needed
- Q009, Q032 (no header text in top margin) → already covered by P034/P041; no new detector needed
- Q048, Q062, Q071 (continued headings) → already covered by P030; no new detector needed
- Q063, Q064, Q072, Q073 (Table/Figure/Page labels) → already covered by P031; no new detector needed
- Q013, Q021, Q036, Q047, Q061, Q070 (heading format: all caps, bold, centered) → P038 covers phrase
  presence; P014 split should add dedicated format checks for bold/centered/top-of-page

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

**Additional body-text questions (Ester's new proposed questions, not in Q-matrix):**
1. Is the first paragraph after level 1, 2, 3, and 4 titles NOT indented?
2. Are all body paragraphs indented, excluding the initial paragraph following heading levels 1–5?

**Implementation plan:**
- Q002/Q003 → already partially covered by P044 (abstract indentation) and P015
- Q044/Q045 → already partially covered by P043 (acknowledgements indentation) and P015
- PR 2 should add separate atomic rule IDs for each section's checks instead of routing through P015
- Body-text indentation questions require new detector sub-checks in `pdf_body_indentation.py`

---

## PR 3: Split P017 into Atomic Caption/Title Checks

**Current rule:** P017 — "Do figure/table caption and title lines show obvious formatting issues?"
Covers all caption/title formatting.

**Ester's atomic checks with Q-matrix mapping:**

| Check | Type | Q-Rule | Overlap with existing P-rule? |
|-------|------|--------|-------------------------------|
| Figure captions in sentence case | Figure | Q074 | P017 partial — needs new sub-check |
| Figure captions end with terminal period | Figure | Q075 | P040 already covers this in LoF |
| Figure captions single-spaced/justified | Figure | Q076 | P032 already covers wrapped entry spacing |
| Figure label "Figure N." is bold | Figure | (new) | Not in Q-matrix; no P-rule; low priority |
| Table titles in title case, no terminal period | Table | Q065 | P053 covers LoT titles; P017 partial |
| Multi-line table titles single-spaced | Table | Q066 | P032 already covers wrapped entry spacing |

**Implementation plan:**
- Q074 (figure sentence case) → new sub-check in `pdf_captions.py`; no existing P-rule covers this
- Q075 (terminal punctuation) → P040 already handles this in List of Figures
- Q076, Q066 (single-spaced wraps) → P032 already handles this
- Q065 (table title case) → P053 handles LoT title case; P017 may need separate figure/table dispatch
- Split `pdf_captions.py` into figure-specific and table-specific checks when implementing

---

## PR 3: Split P018 into Atomic TOC/LoT/LoF Alignment Checks

**Current rule:** P018 — "Do TOC/List of Tables/List of Figures entries show likely alignment inconsistencies?"
Combined alignment rule.

**Ester's atomic checks with Q-matrix mapping:**

### TOC checks (Q049–Q059):

| Q-Rule | Check | Overlap with existing P-rule? |
|--------|-------|-------------------------------|
| Q049 | Level-1 TOC entries in ALL CAPS | P018 and P024 partial |
| Q050 | Level-2 TOC entries in Title Case | P018 and P024 partial |
| Q051 | Level-3 TOC entries in Sentence Case | P018 and P024 partial |
| Q052 | Consistent leader style (dots/hyphens) | P018 partial |
| Q053 | Wrapped level-1 TOC entries single-spaced internally | P032 already covers this |
| Q054 | Wrapped level-2 TOC entries single-spaced internally | P032 already covers this |
| Q055 | Wrapped level-3 TOC entries single-spaced internally | P032 already covers this |
| Q056 | Level-2 and level-3 entries indented relative to parent | P039 already covers this |
| Q057 | Visible double spacing between consecutive TOC entries | P036 already covers this |
| Q058 | Single appendix entry begins with "APPENDIX" plus title | P042 already covers this |
| Q059 | Multiple appendix entries identified by letters (A, B…) | P042 already covers this |

### List of Tables checks (Q065–Q069):

| Q-Rule | Check | Overlap with existing P-rule? |
|--------|-------|-------------------------------|
| Q065 | Table titles in title case, no final period | P053 already covers this |
| Q066 | Wrapped table titles single-spaced internally | P032 already covers this |
| Q067 | Visible double spacing between consecutive LoT entries | P036 already covers this |
| Q068 | Table numbers aligned in left column | P046 already covers this |
| Q069 | Page numbers aligned in right column | P048 already covers this |

### List of Figures checks (Q074–Q079):

| Q-Rule | Check | Overlap with existing P-rule? |
|--------|-------|-------------------------------|
| Q074 | Figure descriptions in sentence case | P017 partial; needs new sub-check |
| Q075 | Every figure description ends with terminal punctuation | P040 already covers this |
| Q076 | Wrapped figure descriptions single-spaced internally | P032 already covers this |
| Q077 | Visible double spacing between consecutive LoF entries | P036 already covers this |
| Q078 | Figure numbers aligned in left column | P046 already covers this |
| Q079 | Page numbers aligned in right column | P048 already covers this |

**Implementation plan:**
- Q053-Q059 (wrapped spacing, indentation, appendix) → mostly already covered by P032/P036/P039/P042
- Q049-Q052 (TOC capitalization levels, leader) → P018/P024 partially cover these; split into atomic sub-checks
- Q065-Q069 (LoT) → mostly already covered by P053/P032/P036/P046/P048
- Q074-Q079 (LoF) → mostly already covered by P040/P032/P036/P046/P048; Q074 (sentence case) is the gap
- Cross-reference existing rules before adding new detectors to avoid duplication

---

## PR 4: P026 Accepted Font Policy Decision

**Current behavior:** Computer Modern (CMR) is flagged as non-Times.
**Ester's guidance:** Word users → Times New Roman (and Arial per notes); Overleaf users → Computer Modern is accepted.

**Current state after PR 1:** Wording updated to say "Computer Modern is an accepted equivalent — if flagged, verify with your advisor." CMR is still flagged but remediation guides students to verify.

**Decision needed:**
- Option A: Add CMR to the accepted font list in `pdf_font_compliance.py` (stops flagging for Overleaf users)
- Option B: Keep flagging CMR but note "verify with advisor" in remediation (current approach after PR 1)
- Option C: Detect document source (Word vs. LaTeX/Overleaf) and apply different font policies per source

**Recommendation:** Option A after confirming with NJIT policy. The current Option B remediation already says "verify with advisor" as a bridge. Arial for Word users may also need to be added if NJIT confirms it is acceptable for body text (requires policy confirmation before implementing).

---

## PR 5: Unimplemented Q-Rules (Require NLP/Semantic Analysis)

### Acknowledgements content (Q037–Q043):

| Q-Rule | Check |
|--------|-------|
| Q037 | First paragraph explicitly thanks the advisor(s) |
| Q038 | Second paragraph explicitly thanks the committee members |
| Q039 | Third paragraph mentions both technical and financial support |
| Q040 | Grant support includes full agency name and grant number in parentheses |
| Q041 | Fifth paragraph explicitly mentions peers, colleagues, or fellow students |
| Q042 | Sixth paragraph (if present) explicitly mentions family or friends |
| Q043 | Every named person is identified by full first and last name |

### Approval Page committee ordering (Q015–Q020):

| Q-Rule | Check |
|--------|-------|
| Q015 | Every committee-member entry begins with an honorific (Dr., Mr., Ms.) |
| Q016 | Dissertation Advisor entries appear before non-advisor entries |
| Q017 | Committee members listed in descending rank order |
| Q018 | Same-rank members alphabetized by surname |
| Q019 | External/non-NJIT entries appear after all NJIT entries |
| Q020 | External entries include institution/company name plus city and state |

**Note:** These content checks require NLP/semantic analysis beyond PDF text extraction. Q037–Q043 need natural-language understanding of paragraph intent; Q015–Q020 need entity recognition and rank classification. Implement in PR 5 using an NLP pipeline or defer to manual review guidance.

---

## Q-to-P Coverage Summary

| Coverage status | Count | Q-rules |
|-----------------|-------|---------|
| Already fully covered by another P-rule | 29 | Q001, Q008, Q009, Q012, Q014, Q032, Q048, Q053, Q054, Q055, Q056, Q057, Q058, Q059, Q062, Q063, Q064, Q066, Q067, Q068, Q069, Q071, Q072, Q073, Q075, Q076, Q077, Q078, Q079 |
| Partially/heuristically covered; needs atomic split | 10 | Q013, Q021, Q036, Q047, Q049, Q050, Q051, Q052, Q061, Q070 |
| Not yet implemented (no P-rule) | 7 | Q037, Q038, Q039, Q040, Q041, Q042, Q043 |
| Other (partial coverage via P068/P025/P066/P067) | 10+ | Q007, Q015–Q020, Q023, Q024, Q027, Q030 |
