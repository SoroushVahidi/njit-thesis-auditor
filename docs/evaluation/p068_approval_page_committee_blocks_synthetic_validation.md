# P068 Approval Page Committee Blocks — Synthetic Validation

- **Rule:** P068 — Approval Page committee/signature-block structural check
- **Q-rule basis:** Q013 structural extension (Q015–Q020 manual-only)
- **Module:** `njit_auditor.rules.pdf_approval_page_committee_blocks`
- **Issue types:** `approval_page_advisor_role_label_missing`, `approval_page_signature_blocks_sparse`
- **Validation date:** 2026-06-08

## Purpose

P068 provides conservative PDF-only coverage for the NJIT Approval Page structural
expectation that committee role labels and signature/date blocks are present on a uniquely
detected `APPROVAL PAGE`. The rule uses template phrase matching and structural counts only.

## Scope

Implemented in v1:

- unique `APPROVAL PAGE` heading detection via `find_named_frontmatter_headings()`
- body-line scan below the heading
- advisor/committee role-label phrase counting in line prefixes
- date label, signature label, and underscore-blank indicator counting
- sparse advisor-role and sparse signature-block warnings

Explicitly out of scope:

- committee-member identity validation
- honorific checks (Q015)
- advisor-first ordering (Q016)
- rank order, alphabetical order, NJIT/external ordering (Q017–Q019)
- external institution completeness (Q020)
- signature authenticity or visual signature detection
- OCR or image analysis
- quotation of approval-page body text in findings

## Synthetic Coverage

`tests/test_p068_approval_page_committee_blocks.py` covers 13 scenarios:

| Test | Scenario | Expected result |
|---|---|---|
| 1 | No approval page | No findings |
| 2 | Complete synthetic approval page | No findings |
| 3 | Committee labels without advisor phrase | `approval_page_advisor_role_label_missing` |
| 4 | Advisor label but no date/signature indicators | `approval_page_signature_blocks_sparse` |
| 5 | Below body/role-label gates | No findings |
| 6 | Multiple `APPROVAL PAGE` headings | No findings |
| 7 | Image-only / empty text layer | No findings |
| 8 | Underscore blanks counted as indicators | No sparse finding |
| 9 | `Major Professor` counts as advisor label | No advisor-missing finding |
| 10 | `committee` word in non-approval body prose | No findings |
| 11 | Privacy: no placeholder names in details | Pass |
| 12 | Substantial lines but zero role labels | No findings |
| 13 | Manual-only semantics not emitted | Pass |

## Finding Payload

When P068 fires, details are limited to privacy-safe metadata:

- `page_number`
- `issue_type`
- `role_label_count`
- `advisor_label_present`
- `date_label_count`
- `signature_label_count`
- `signature_blank_count`
- `signature_date_indicator_count`
- `confidence`
- `triage_tier`
- `source_q_rule_ids`

No committee names, advisor names, signature text, dates from real files, or approval-page
prose are included.

## Limitations

- Template phrase list may miss department-specific advisor labels.
- Signature lines rendered as images are not counted as indicators.
- Single-page scan only; multi-page approval blocks are deferred.
- Zero findings on an evaluation PDF do not prove compliance when detection gates skip.
