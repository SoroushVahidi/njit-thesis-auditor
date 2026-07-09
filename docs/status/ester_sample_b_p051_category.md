# Ester Sample B P051 Category Fix

**Recorded:** 2026-07-09
**Branch:** `fix/ester-sample-b-p051-copyright-category`
**Base:** `main` @ `963fe93` (PR #482 and PR #484 merged)

## Scope

Narrow follow-up to `docs/status/ester_sample_b_feedback_audit.md` item SB-17.
Ester confirmed the P051 (`copyright_year_not_found`) finding on Sample B
page 4 is correct, but objected to its student-facing category: the report
showed it under **Title page**, when it belongs on the **Copyright page**.

Out of scope (left for later, separate branches): P011, P019, P038, P023,
P020, P063/P026 font, and the duplicate spacing section — all still tracked
in `docs/status/ester_sample_b_feedback_audit.md`.

## Root Cause

Category is not stored on `AuditFinding` itself. It's computed on the fly by
`map_finding_rule_to_category()` in `src/njit_auditor/evaluation.py`, which
had `"P051": "title_page_metadata"`. That raw key is humanized for the web
report via `_CATEGORY_LABELS["title_page_metadata"] = "Title page"` in
`src/njit_auditor/web_app.py`. Every rule sharing that mapping (P033, P034,
P041, P052, Q006) legitimately covers title-page content; P051 didn't,
since it's the Copyright Page's missing-year check
(`src/njit_auditor/rules/pdf_copyright_page.py`).

## Fix

- `evaluation.py`: `"P051"` now maps to a new category key,
  `"copyright_page_metadata"`, instead of `"title_page_metadata"`.
- `web_app.py`: added `"copyright_page_metadata": "Copyright page"` to
  `_CATEGORY_LABELS`.
- No other rule's category mapping changed — P033/P034/P041/P052/Q006 still
  map to `title_page_metadata` / "Title page", since those are correctly
  on the Title Page.
- The P051 rule ID, detector logic (`check_pdf_copyright_year_format`), and
  finding message/details are all unchanged.

## Result

- Sample B P051 (page 4) now reports under **Copyright page**, not
  **Title page**, in the web UI's category filter, "Findings by topic"
  index, and any other view driven by `finding.category` /
  `_humanize_cat`.
- Markdown export's "Counts by Category" section now lists
  `copyright_page_metadata` for P051 instead of `title_page_metadata`
  (same raw-snake-case style as all other categories in that section).
- P051's own finding/message/rule ID are byte-for-byte unchanged; only the
  category label moved.

## Files Changed

- `src/njit_auditor/evaluation.py`
- `src/njit_auditor/web_app.py`
- `tests/test_evaluation.py`
- `tests/test_pdf_rules.py`

## Tests

Added:

- `test_evaluation.py::test_rule_id_mapping` — extended with
  `map_finding_rule_to_category("P051") == "copyright_page_metadata"`.
- `test_pdf_rules.py::test_p051_category_is_copyright_page_not_title_page` —
  builds a synthetic copyright page missing a year, confirms the P051
  finding is still produced, its `report_view` category is
  `copyright_page_metadata`, `_humanize_cat` renders "Copyright page" (not
  "Title page"), the JSON export keeps `rule_id == "P051"`, and the
  markdown export renders without error and still contains `` `P051` ``.

Existing P051 detector tests (`test_p051_no_year_warns`,
`test_p051_p034_unaffected`, etc.) and the `_CATEGORY_LABELS`
completeness/uniqueness tests in `test_web_app.py` continue to pass
unchanged.

Targeted:

```bash
/home/soroush/njit-thesis-auditor/main/.venv/bin/python -m ruff check .
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q \
  tests/test_pdf_rules.py -k 'p051 or copyright' \
  tests/test_ester_sample_a_correctness.py
```

Full suite:

```bash
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q
```

Result: **2670 passed, 4 warnings** (ruff: all checks passed).

## Deferred / Still Open

Per `docs/status/ester_sample_b_feedback_audit.md`, resolving this leaves the
rest of Sample B's concern list open for future branches:

- P011 low-overflow margin false positives (pages 1, 24, 39).
- P019 highlight targeting + document-level numbering presentation.
- P038 Acknowledgements false positive (page 9) + per-page front-matter
  handling.
- P023 figure-description spacing exception (page 82).
- P020 heading-level vs table-title specific wording (pages 71, 80).
- Duplicate P016 spacing presentation on page 1.
- P026 page-5 font highlight/feedback accuracy.
- Sample B P015 page 34 residual finding (unrelated to page 23's fix,
  not in Ester's concern list).
