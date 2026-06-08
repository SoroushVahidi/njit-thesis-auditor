# P066 — Biographical Sketch Structural/Ordering Check: Scope and Design

## 1. Metadata

- **Rule ID:** P066
- **Rule name:** Biographical Sketch Structural/Ordering Check
- **Date scoped:** 2026-06-08
- **Baseline commit:** `cf3b533` (post PR #234)
- **Status:** Scoped only — not yet implemented
- **Validation baseline:** 925 pytest, ruff clean, mypy 83 source files
- **Source Q-rules:** Q025 (primary); Q023, Q024 (deferred)
- **Module (planned):** `src/njit_auditor/rules/pdf_biosketch_degree_ordering.py`
- **Companion rules:** P045 (`pdf_biosketch_publication_layout.py` — Q028/Q029),
  P047 (`pdf_biosketch_bullet_spacing.py` — Q026),
  P038 (`pdf_frontmatter_headings.py` — Q021 heading presence)

---

## 2. Motivation

After P064 (references/citations structural check) and P065 (dedication
centering/italic), the remaining unimplemented bio-sketch Q-rules are
Q023–Q025.  The full-repository audit (`docs/status/full_repository_audit_after_p063.md`)
identified these as the next candidate gap after the references/citations
and dedication checks.

Bio-sketch checks are a meaningful next target because:

1. The Biographical Sketch is required front matter in NJIT dissertations.
2. Q025 (degree chronological ordering) is the most structurally checkable
   of the three remaining rules without reading biographical content.
3. P045 and P047 already handle publication layout and bullet spacing on the
   bio-sketch page; this rule addresses the orthogonal ordering concern.

Bio-sketch checks require careful scoping because the page contains
personal biographical content — degree history, institutional affiliations,
publication records. Reading or reproducing this content would violate the
project's privacy model. Only geometric/structural metadata and anonymized
counts may appear in findings.

---

## 3. Guideline / Q-Rule Basis

**Source files:**
- `data/raw/guidelines/260330_YESNO_audit_logic_matrix.xlsx`
- `data/raw/guidelines/Self-Self Assessment Sheet.pdf`

| Q-rule | Short paraphrase | Automatable in v1? | Notes |
|--------|-----------------|-------------------|-------|
| Q023 | Bio sketch must not include place or date of birth | **No — manual only** | Requires reading and understanding biographical content; high privacy risk; NLP needed for reliability |
| Q024 | Bio sketch must not include work experience or employment history | **No — manual only** | Requires reading and understanding content; high privacy risk; NLP needed |
| Q025 | Postgraduate degrees listed most recent to oldest; NJIT degree listed first when applicable | **Partial — year ordering only** | Year-pattern detection in education-section lines is feasible; "NJIT first" sub-requirement deferred (requires institution text recognition) |

**Already covered by existing rules:**
- Q021 (BIOGRAPHICAL SKETCH heading presence) — partially covered by P038
- Q022 (bio sketch page number "iv") — partially covered by page numbering rules
- Q026 (bullet single-spacing) — partially covered by P047
- Q028 (publication entry inter-spacing) — partially covered by P045
- Q029 (publication hanging indent) — partially covered by P045

**Prior analysis note:** `docs/status/q_rule_coverage_after_p044.md` previously
marked Q023–Q025 as "Defer" with reasons:
- Q023: "High privacy risk; NLP needed for reliability"
- Q024: "High privacy risk; NLP needed"
- Q025: "Date parsing; moderate FP risk"

This scoping document addresses Q025 only, with a conservative algorithm
designed to minimize false positives.

---

## 4. P066 v1 Scope

### What P066 should check (v1)

**Q025 — degree chronological ordering (structural year-pattern heuristic):**

On the Biographical Sketch page, collect text lines in the education-section
zone (below the BIOGRAPHICAL SKETCH heading and above any detectable
Publications/Presentations sub-section boundary). Identify lines that match
a short-line / single-year-token pattern consistent with education entries.
Check whether the year tokens extracted from those lines are in non-increasing
order (most recent first). If the order is clearly violated and there are
enough high-confidence year candidates, emit `biosketch_degree_order_suspicious`.

Issue type: `biosketch_degree_order_suspicious`

### What P066 should NOT check (v1)

- Whether the bio sketch contains birth date or birthplace (Q023 — manual only)
- Whether the bio sketch contains work experience or employment (Q024 — manual only)
- Whether the NJIT degree appears first (Q025 "NJIT first" sub-requirement — deferred;
  requires recognizing institution name text)
- Whether publication entries are in chronological order (Q027 — citation text required)
- Whether the bio sketch narrative is professionally written (manual only)
- Whether the biography is accurate, complete, or correctly represents the author (manual)
- Any check requiring reading, understanding, or reproducing biographical text content

### Input type

PDF text layer only. TeX source support deferred.

---

## 5. Detection Algorithm

### 5.1 Bio sketch page detection

Reuse the same pattern as P045 and P047:

```python
from njit_auditor.rules.pdf_headings import find_named_frontmatter_headings

_HEADING_LABEL = "BIOGRAPHICAL SKETCH"

def _find_biosketch_page_and_heading_y(pdf_doc) -> tuple[PdfPage, float] | None:
    for match in find_named_frontmatter_headings(pdf_doc):
        if match.heading != _HEADING_LABEL:
            continue
        # find heading line y1 on matched page
        ...
    return None
```

Return `None` if zero or more than one BIOGRAPHICAL SKETCH heading is found
(ambiguous), or if the page is image-only (no text blocks).

### 5.2 Education-zone boundary detection

After the bio sketch heading, look for a sub-section label consistent with
"Publications and Presentations" or "Undergraduate and Graduate Education"
(common section label patterns). Lines above the Publications label and below
the bio sketch heading form the education zone.

If no Publications boundary is detectable, treat all lines below the heading
as candidates but apply stricter year-pattern filtering.

### 5.3 Education-entry candidate line identification

A line is an education-entry candidate if it meets ALL of:
- Located in the education zone (below heading, before Publications boundary
  if detected)
- Short enough to be a degree-entry line rather than narrative prose:
  raw line length ≤ `_MAX_DEGREE_LINE_CHARS = 120`
- Contains exactly one 4-digit year token in range `_YEAR_MIN = 1960` to
  `_YEAR_MAX = 2100`
- Does not match the page-number exclusion pattern
- Text contains at least one alpha character (not purely numeric/punctuation)

### 5.4 Year extraction

Extract the single year integer from each candidate line. The year is the
structural metadata used for ordering analysis — not the line text.

### 5.5 Ordering check

Collect extracted years in top-to-bottom page order.

Gates:
- Skip if fewer than `_MIN_YEAR_CANDIDATES = 3` candidate lines found.
- Skip if all extracted years are equal (cannot determine order).
- Skip if only 2 candidates (too few to distinguish order from coincidence).

Check: is the year sequence non-increasing? (Each year ≤ previous year means
"most recent first", which is correct.)

If the sequence is NOT non-increasing AND at least one inversion exists where
the later-listed year is more than `_MIN_YEAR_GAP = 2` years larger than the
earlier-listed year, emit `biosketch_degree_order_suspicious`.

The `_MIN_YEAR_GAP` threshold avoids flagging same-year entries (e.g., two
degrees completed in the same calendar year).

### 5.6 Handling split/merged lines from PDF extraction

If the extracted year count is < `_MIN_YEAR_CANDIDATES` after filtering,
skip (do not force detection). This handles cases where PDF text-layer merging
collapses multiple education lines into one.

### 5.7 Image-only and flattened PDFs

If the bio sketch page has no text blocks or all text blocks have
`text == ""`, return no findings immediately after heading detection fails.

---

## 6. Issue Types

| Issue type | Trigger condition |
|---|---|
| `biosketch_degree_order_suspicious` | Year sequence among education-entry candidate lines is not non-increasing (later year > earlier year by > `_MIN_YEAR_GAP`); ≥ `_MIN_YEAR_CANDIDATES` candidates required |

**Not included in v1:**
- `biosketch_birth_date_detected` — not scoped; high privacy risk
- `biosketch_work_experience_detected` — not scoped; high privacy risk
- `biosketch_njit_not_first` — deferred; requires institution text recognition
- `biosketch_institution_line_split` — deferred; requires reading institution names
- `biosketch_heading_not_detected` — covered by P038 (frontmatter headings)

---

## 7. Finding Fields

All fields must be privacy-safe — no text content, no names, no institution
names, no publication text, no biographical prose.

| Field | Type | Description |
|---|---|---|
| `issue_type` | str | Always `"biosketch_degree_order_suspicious"` |
| `page` | int | Bio sketch page number |
| `year_candidate_count` | int | Number of education-entry candidate lines with extracted years |
| `first_candidate_year` | int | Year from the topmost candidate line |
| `last_candidate_year` | int | Year from the bottommost candidate line |
| `inversion_count` | int | Number of adjacent year pairs where later year > earlier year |
| `confidence` | str | `"medium"` — year-pattern heuristic; structural only |
| `triage_tier` | str | `"low"` — moderate FP risk |
| `source_q_rule_ids` | str | `"Q025"` |

**Explicitly excluded from findings:**
- Bio sketch text, sentences, or prose
- Author name, degree name, institution names
- Any year token if it could be from a publication citation rather than degree
- Title text, committee names, body text, source lines

---

## 8. Conservative Skip Conditions

P066 returns no findings when any of the following applies:

| Skip condition | Reason |
|---|---|
| No BIOGRAPHICAL SKETCH heading detected | Cannot locate page |
| Multiple competing BIOGRAPHICAL SKETCH headings | Ambiguous page identification |
| Bio sketch page has no usable text blocks | Image-only or flattened |
| Fewer than `_MIN_YEAR_CANDIDATES = 3` education-entry year candidates | Too sparse to determine ordering |
| All extracted years are equal | Cannot determine order from equal years |
| Year candidates all fall in Publications zone | Candidate lines are publication years, not degree years |
| PDF extraction merges education lines such that year count drops below minimum | Extraction artifact; cannot determine ordering reliably |
| The only inversion is within `_MIN_YEAR_GAP = 2` years | May represent same graduating period; skip to reduce FP |
| Content cannot be judged without reading private biographical prose | Manual review required |

---

## 9. False-Positive and False-Negative Risks

### False-positive risks

- **Year tokens from narrative prose:** A sentence like "I graduated in 2018
  after attending a summer institute in 2015" would produce candidate years
  not representing degree entries. Mitigated by line-length threshold
  (`_MAX_DEGREE_LINE_CHARS = 120`) and requiring exactly one year token per
  candidate line.
- **Year tokens from publication section incorrectly included:** If the
  Publications boundary is not detectable, publication years may pollute the
  candidate set. Mitigated by Publications boundary detection; fall back to
  stricter filtering.
- **International degree entries:** Some degree entries may include two years
  (enrollment and completion, e.g., "2014–2018"). Two-year lines fail the
  "exactly one year token" gate and are correctly excluded.
- **Non-standard bio sketch layouts:** Some authors may list degrees in a
  paragraph format (narrative) without one degree per line. Candidate year
  count < `_MIN_YEAR_CANDIDATES` causes skip.

### False-negative risks

- **Image-rendered bio sketch:** The most common limitation on this dataset.
  All five evaluation PDFs showed no bio sketch via P041/P045 when text
  layers were absent.
- **Correct ordering detected as wrong:** Rare; the non-increasing check is
  simple arithmetic — if years are truly ordered correctly, no inversion
  occurs.
- **Degrees same year:** Two degrees in the same year are not flagged (they
  tie; correct order cannot be asserted from year alone).

### Privacy risks

- Year integers (e.g., 2018) in finding fields are low-sensitivity. They do
  not identify individuals and are within the project's existing practice of
  reporting numeric metadata (page numbers, counts, offsets).
- The algorithm must never store, log, or emit line text, degree names,
  institution names, or any biographical prose.

---

## 10. Synthetic Test Plan

All tests use entirely synthetic PDFs with fake placeholder years. No real
dissertation content, author names, degree text, or institutional names appear
in tests.

| # | Test name | Scenario | Expected |
|---|---|---|---|
| 1 | `test_no_biosketch_page_no_findings` | No BIOGRAPHICAL SKETCH heading | No findings |
| 2 | `test_correct_order_no_findings` | Year candidates: 2023, 2019, 2015 (non-increasing) | No findings |
| 3 | `test_reversed_order_emits_finding` | Year candidates: 2015, 2019, 2023 (increasing — wrong) | `biosketch_degree_order_suspicious` |
| 4 | `test_partial_inversion_emits_finding` | Year candidates: 2023, 2015, 2019 (partial inversion) | `biosketch_degree_order_suspicious` |
| 5 | `test_too_few_candidates_skips` | Only 2 year-bearing lines | No findings |
| 6 | `test_equal_years_skips` | All candidates same year | No findings |
| 7 | `test_inversion_within_gap_skips` | Years: 2020, 2021 (delta = 1 ≤ `_MIN_YEAR_GAP = 2`) | No findings |
| 8 | `test_image_only_page_no_findings` | Page with no text blocks | No findings |
| 9 | `test_multiple_biosketch_headings_skips` | Two BIOGRAPHICAL SKETCH headings | No findings |
| 10 | `test_publication_zone_excluded` | Candidate years only in Publications section | No findings |
| 11 | `test_finding_fields_are_privacy_safe` | Reversed order → finding | Finding detail values contain no bio text, names, or prose |
| 12 | `test_finding_rule_id_is_p066` | Any emitted finding | `rule_id == "P066"` |

Total: 12 tests (satisfies ≥ 10–12 requirement).

---

## 11. Current-Dataset Evaluation Plan

After implementation:

1. Extract Sebastian Fine from ZIP; use four tracked PDFs directly.
2. Run P066-only on all five evaluation PDFs.
3. Collect per-file counts: total findings, `biosketch_degree_order_suspicious` count,
   bio sketch page detected (yes/no), skip reason if applicable.
4. Report aggregate count only.
5. Do NOT quote bio-sketch content, degree names, institution names, or years from
   real files unless years are already in finding fields.
6. Note expected limitation: if bio sketch pages are image-rendered (as seen with
   P041/P045 on this dataset), P066 will return 0 findings on all files.

---

## 12. Implementation Checklist

- [ ] New module: `src/njit_auditor/rules/pdf_biosketch_degree_ordering.py`
- [ ] Wire into `collect_pdf_layout_findings()` after P065 in `src/njit_auditor/audit_runner.py`
- [ ] Add `"P066"` to `PDF_AUDIT_POST_P054_RULE_IDS` tuple
- [ ] Add `"check_pdf_biosketch_degree_ordering"` to `PDF_AUDIT_POST_P054_CALLABLE_NAMES`
- [ ] Add P066 → `"frontmatter_structure"` to `evaluation.py` category mapping
- [ ] Add P066 entry to `data/processed/rules/project_added_rules.json` (66 total)
- [ ] Update `tests/test_rule_inventory.py`: count 65 → 66, P066 assertions
- [ ] Update `tests/test_audit_runner.py`: parity tuple assertions for P066
- [ ] Tests: `tests/test_p066_biosketch_degree_ordering.py` (≥ 12 tests)
- [ ] Synthetic validation doc: `docs/evaluation/p066_biosketch_degree_ordering_synthetic_validation.md`
- [ ] Privacy test: no bio-sketch text in findings
- [ ] Status docs update: `current_project_state_and_next_steps.md`
- [ ] Validation: `ruff check .`, `mypy src`, `python -m pytest` (expect 937: 925 + 12)

---

## 13. Recommendation

**P066 is ready for implementation** with the conservative Q025-only heuristic
described in this document.

The issue type `biosketch_degree_order_suspicious` is well-defined, privacy-safe,
and defensible: it operates on year integers extracted from short candidate lines
and never reads or reproduces biographical prose.

**Caveats:**
- Q023 and Q024 remain manual-only and are out of scope for P066.
- The "NJIT first" sub-requirement of Q025 is deferred because institution
  name recognition would require reading text content.
- Moderate false-positive risk from year patterns in narrative prose; addressed
  by the line-length threshold, one-year-per-line gate, and minimum candidate
  count.
- If the current evaluation dataset has image-rendered bio sketch pages (as seen
  with P041/P045), P066 will produce 0 findings — this is expected and does not
  indicate non-compliance.

**Next PR:** `rules/p066-biosketch-degree-ordering` — implement P066 exactly per
this scope document.

**If P066 effectiveness is low on the current dataset** (due to image-only bio
sketches), consider P067 targeting a gap in a section with better text-layer
coverage (e.g., publications date ordering Q027, abstract structural checks, or
a tighter front-matter structure refinement).
