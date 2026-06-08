# P069 Front-Matter Heading Gate Recall — Synthetic Validation

- **Date:** 2026-06-08
- **Auditor scope:** P001–P069 implemented
- **Type:** Infrastructure / gate refinement only (no standalone P069 findings)
- **Module:** `src/njit_auditor/rules/pdf_frontmatter_heading_gate.py`
- **Privacy:** Synthetic fixtures only; no real dissertation or EF comment text quoted.

---

## Purpose

Validate the shared P069 gate resolver that improves canonical front-matter heading
localization for dependent rules without changing P014 strict style checks.

## Affected rules

| Rule | Gate consumer change |
|---|---|
| P041 | Dedication page localization |
| P044 | Abstract page localization |
| P045 | Biographical Sketch localization |
| P046 | LoT/LoF page detection (via TOC/list detector) |
| P047 | Biographical Sketch localization |
| P065 | Dedication page localization |
| P066 | Biographical Sketch localization |
| P067 | Biographical Sketch localization |
| P068 | Approval Page localization |

## Infrastructure-only nature

P069 emits **no standalone findings** in v1. Increased findings appear only when
dependent rules previously skipped at heading gates and downstream checks then run.

## Q-rule / guideline basis (paraphrased)

Partial gate-refinement support for Q013, Q021, Q031–Q032, Q035–Q036, Q047, Q061,
Q070. Semantic checks (Q015–Q020, Q039–Q043) remain out of scope.

## Synthetic test coverage

`tests/test_p069_frontmatter_heading_gate_recall.py` — **13 tests**:

| Scenario | Result |
|---|---|
| Exact `BIOGRAPHICAL SKETCH` | Canonical match (`high`) |
| `ACKNOWLEDGMENTS` variant | Maps to `ACKNOWLEDGEMENTS` (`medium`) |
| `LIST OF TABLES (Continued)` | Maps to `LIST OF TABLES` (`medium`) |
| Long prose with embedded heading phrase | No match |
| Long prose with `DEDICATION` token | No match |
| Heading on body-classified page | No gate match |
| Image-only page | No gate match |
| P068 exact approval page baseline | Unchanged (no findings) |
| P066 via trailing-colon bio-sketch variant | Gate reached; strict matcher skipped |
| Multiple approval-page matches | Ambiguous skip preserved |
| Resolver metadata privacy | No raw line text exported |
| Strict synthetic dedication doc | Centering finding unchanged |
| P065 dedication gate privacy | No placeholder text in findings |

Regression: existing P065/P066/P068 synthetic suites pass unchanged.

## Privacy model

- Resolver returns canonical heading labels and match-path metadata only.
- No raw heading line text from real PDFs in findings or committed docs.
- Synthetic fixtures use clearly fake placeholder strings only.

## Limitations

- No OCR; image-only headings remain undetectable.
- No fuzzy typo matching beyond curated variant map.
- LoT/LoF **entry** parsing remains a separate follow-up track.
- Improved heading recall does not prove guideline compliance.
