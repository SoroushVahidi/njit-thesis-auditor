# P038 Synthetic Validation — Front-Matter Exact Heading Phrase and Missing-Section Checks

- **Date:** 2026-06-02
- **Rule:** P038 — PDF front-matter exact heading phrase and missing-section checks
- **Module:** `src/njit_auditor/rules/pdf_frontmatter_headings.py`
- **Test file:** `tests/test_pdf_rules.py` (12 P038 tests)
- **Validation type:** Synthetic only — no evaluation PDFs available in workspace

---

## Scope

P038 checks that required front-matter headings are present and use the canonical NJIT phrase.

| Check | Required headings |
|-------|------------------|
| `required_heading_missing` | APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS |
| `heading_phrase_not_exact` | Known curated variant: "ACKNOWLEDGMENTS" → expected "ACKNOWLEDGEMENTS" |
| Gate | No findings if no headings detected at all (flattened/image-only PDFs) |
| Optional headings (not flagged as missing) | DEDICATION, LIST OF TABLES, LIST OF FIGURES |

P038 does not duplicate P014 style checks (bold/centered/near-top/all-caps) or P025 structure checks (abstract body, title-page elements).

---

## Synthetic Test Results

| Test | Fixture | Expected behavior | Result |
|------|---------|-------------------|--------|
| All required headings correct | APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS, Chapter | No finding | ✅ Pass |
| APPROVAL PAGE missing | Bio, Ack, TOC, Chapter | `required_heading_missing` for approval_page | ✅ Pass |
| BIOGRAPHICAL SKETCH missing | Approval, Ack, TOC, Chapter | `required_heading_missing` for biographical_sketch | ✅ Pass |
| ACKNOWLEDGEMENTS missing | Approval, Bio, TOC, Chapter | `required_heading_missing` for acknowledgements | ✅ Pass |
| TABLE OF CONTENTS missing | Approval, Bio, Ack, Chapter | `required_heading_missing` for table_of_contents | ✅ Pass |
| "ACKNOWLEDGMENTS" (American spelling) | Approval, Bio, ACKNOWLEDGMENTS, TOC, Chapter | `heading_phrase_not_exact`; expected ACKNOWLEDGEMENTS | ✅ Pass |
| DEDICATION absent | All required present, no DEDICATION, Chapter | No finding (optional) | ✅ Pass |
| LIST OF TABLES / FIGURES absent | All required present, no LOT/LOF, Chapter | No finding (optional) | ✅ Pass |
| No headings detected at all | Plain body text, no heading | No finding (gate) | ✅ Pass |
| Finding metadata privacy-safe | ACKNOWLEDGMENTS variant | observed_heading_normalized = "ACKNOWLEDGMENTS" only; no arbitrary text | ✅ Pass |
| LIST OF TABLES and FIGURES correct | All headings present and exact | No finding | ✅ Pass |
| CLI integration | ACKNOWLEDGMENTS variant → JSON output | P038 in findings | ✅ Pass |

All 12 tests pass.

---

## Issue Types

| Issue type | Trigger |
|-----------|---------|
| `required_heading_missing` | A required heading (APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS) not detected in front matter when at least one other heading is detected |
| `heading_phrase_not_exact` | A known curated safe variant (ACKNOWLEDGMENTS) detected in front-matter top zone |

---

## Privacy Notes

- `required_heading_missing` findings include only: `section_key`, `expected_heading`, `issue_type`, `triage_tier`, `confidence`. No body text.
- `heading_phrase_not_exact` findings include: `section_key`, `expected_heading`, `observed_heading_normalized` (only for known safe curated variants, never arbitrary extracted text), `issue_type`, `triage_tier`, `confidence`.
- No dissertation body text, section body prose, author names, committee names, or private content is included in any finding.

---

## Current-Dataset Evaluation

No current-dataset evaluation was run. Evaluation PDFs are unavailable in the workspace.
When evaluation PDFs become available, rerun locally into:

```
data/evaluation/generated/current_auditor_after_p038/
```

Do not commit generated outputs. Document aggregate P038 counts only in a future
`docs/evaluation/p038_current_dataset_evaluation.md`.

---

## Known Limitations

- **Curated variant list is small:** Only "ACKNOWLEDGMENTS" is in `_KNOWN_VARIANTS` v1. Other misspellings (e.g., "ACKNOWLEDGMENT", "BIOGRAPHICAL SKETCHES") are not detected, to avoid false positives from arbitrary text.
- **Flattened/image-only PDFs:** The gate (no headings detected → skip) prevents false positives when no text layer is extractable, but also means P038 silently passes on truly flattened PDFs.
- **Optional heading scope:** LIST OF TABLES and LIST OF FIGURES are never flagged as `required_heading_missing`. Theses without tables or figures correctly receive no finding. Theses that should have LOT/LOF but omit it will also receive no finding from P038.
- **APPROVAL PAGE false negatives:** Some PDFs may use an alternate phrase or embed the approval content without a distinct heading line; P038 would not detect the absence.
