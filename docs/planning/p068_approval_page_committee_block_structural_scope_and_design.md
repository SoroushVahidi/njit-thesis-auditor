# P068 — Approval Page Committee Block Structural Check: Scope and Design

## 1. Metadata

| Field | Value |
|---|---|
| **P-rule** | P068 |
| **Rule name** | Approval Page Committee Block Structural Check |
| **Date** | 2026-06-08 |
| **Baseline commit** | `ee7af73` (PR #241 — post-P067 aggregate evaluation snapshot) |
| **Status** | **Scoped only — not implemented** |
| **Validation baseline** | 950 pytest (`ruff check .`, `mypy src`) |
| **Planned module** | `src/njit_auditor/rules/pdf_approval_page_committee_blocks.py` |
| **Companion rules** | P014 (`pdf_headings.py` — Q013 layout), P025 (`pdf_frontmatter_structure.py` — sparse body), P038 (`pdf_frontmatter_headings.py` — heading presence), P022 (`pdf_frontmatter_no_page_number.py` — Q014) |

---

## 2. Post-P067 Backlog Audit Summary

### Repository state (audit date 2026-06-08)

| Item | Value |
|---|---|
| Branch | `main` (clean working tree at `ee7af73`) |
| Highest implemented P-rule | **P067** |
| Implemented P-rule count | **67** (`P001`–`P067`) |
| Q-rules in inventory | **79** total |
| Q-rule `implemented` | **2** (Q004, Q005) |
| Q-rule `partially_implemented` | **56** |
| Q-rule `not_implemented` | **21** (9 manual-only, 12 automatable gaps per strict framing) |
| Pytest count | **950** |
| Full aggregate snapshot | `docs/evaluation/current_auditor_after_p067_evaluation.md` — **1,587** findings; P067 adds **0** |

### Inventory lag corrected in this PR

The Q-rule inventory still marked several recently implemented rules as uncovered. Status
notes are updated for:

| Q-rule | Prior inventory status | Actual coverage (code + eval docs) |
|---|---|---|
| Q025 | `not_implemented` | **Partial** — P066 degree year-ordering heuristic |
| Q026 | `not_implemented` | **Partial** — P047 bio-sketch bullet single-spacing |
| Q033 | `not_implemented` | **Partial** — P065 dedication centering |
| Q034 | `not_implemented` | **Partial** — P065 dedication italic |

Q027 was already `partially_implemented` with P067 notes.

### Remaining EF-overlap automatable gaps (after P064–P067)

| EF category | EF comments (2-file set) | Tool coverage at P067 | Notes |
|---|---:|---|---|
| `references_citations` | 9 | **Partial** — P064 structural checks | Style/content semantics remain manual |
| `committee_approval_page` | 5 | **None** | Highest remaining automatable EF miss |
| `list_of_tables_figures_toc` | 4 | Sparse on comparison PDFs | Parser recall issue, not a clean new rule |
| `unclear_or_other` | 88 | N/A | Permanent manual-only gap |

### No existing P068/P069 planning docs

Confirmed: no prior `p068_*` or `p069_*` files under `docs/planning/` before this document.

---

## 3. Motivation

After P064 (references structural), P065 (dedication centering/italic), P066 (bio-sketch
degree ordering), and P067 (bio-sketch publication ordering), the strongest **new** automatable
gap with confirmed guideline basis and EF-comment support is the **Approval Page committee /
signature-block structure**.

Why this is the best next P068 candidate:

1. **EF overlap:** `committee_approval_page` has **5** annotation objects and **0** tool findings
   on the two extractable-comment PDFs (`docs/evaluation/ef_overlap_after_p063_evaluation.md`).
   P064 already addressed the `references_citations` category (9 EF comments).
2. **Guideline basis:** The Approval Page Q-rule cluster (Q013–Q020) and front-matter template
   docs require a committee approval layout with role labels and signature/date blocks.
3. **Non-duplication:** P014 checks heading style; P038 checks heading phrase presence;
   P025 checks only that the page is non-sparse (≥3 substantial lines). None verify that
   expected **role-label and signature/date structural blocks** are present.
4. **Privacy-safe design:** v1 uses template phrase matching and block counts only — no
   committee-member names, honorifics, affiliations, or signature images.
5. **Conservative automation:** Q015–Q020 (honorifics, rank order, NJIT/external ordering,
   institution completeness) remain **manual-only** and are explicitly out of scope.

Parallel refinement track (not P068): shared front-matter heading detection recall would help
P066/P067/P065/P047 on the current dataset (3/5 files skipped at `BIOGRAPHICAL SKETCH`
detection). That is infrastructure work, not a distinct P-rule.

---

## 4. Candidate Comparison (post-P067)

| Candidate | Q/guideline basis | Current coverage | EF motivation | Automatable? | Privacy / FP risk | Decision |
|---|---|---|---|---|---|---|
| **P068 Approval Page committee/signature blocks** | Q013 cluster + template docs | P014/P025/P038 partial | **5 EF comments, 0 tool** | **Yes — structural** | Low privacy; **medium FP** (template variance) | **Selected** |
| Committee rank/order refinement (Q016–Q019) | Q016–Q019 | None | EF semantic | **No — manual** | High privacy; high FP | Deferred |
| LoT/LoF/TOC extraction recall | Q052–Q079 partials | P018/P024/P030–P062 | 4 EF on Yin H | Refinement only | Low privacy; broad scope | Defer as infra |
| Equation numbering/layout | Self-Assessment mentions only | None | None | **No confirmed Q-rule** | Unknown | **Rejected** |
| Appendix/reference placement | P064 deferred note | P042/P063/P064 | Low | Weak Q-rule evidence | Low | Deferred |
| References/citations v2 | P064 v1 scope | P064 implemented | Residual style gaps | Style semantics | Medium-high FP | Deferred |
| Bio-sketch heading recall | Q021 partial | P038/P066/P067 gates | Indirect | Infra refinement | Low | Parallel track |
| Q026/Q030/Q039–Q043 gaps | Mixed | P047 partial; others manual | Low | Q039–Q043 semantic | High privacy | Deferred |

---

## 5. Guideline / Q-Rule Basis

### Source files consulted

| File | Relevance |
|---|---|
| `data/processed/rules/njit_rule_inventory.json` | Q013–Q020 Approval Page cluster |
| `data/raw/guidelines/260330_YESNO_audit_logic_matrix.xlsx` | Authoritative Q-rule definitions (not modified) |
| `data/raw/guidelines/Front Matter Pages Lorem Ipsum.pdf` | Approval page layout template (paraphrased only) |
| `data/raw/guidelines/Self-Self Assessment Sheet.pdf` | Checklist expectations for front matter |
| `docs/evaluation/ef_overlap_after_p063_evaluation.md` | EF `committee_approval_page` gap evidence |

### Q-rule classification for P068

| Q-rule | Paraphrased requirement | Classification for P068 |
|---|---|---|
| Q013 | Approval page shows exact `APPROVAL PAGE` heading in all caps, bold, centered, near top | **Already covered** — P014 layout + P038 phrase presence |
| Q014 | Approval page has no visible page number | **Already covered** — P022 |
| Q015 | Every committee entry begins with honorific | **Manual-only** — requires reading names |
| Q016 | Dissertation Advisor entries before non-advisor entries | **Deferred** — v2 may use y-order of role labels only |
| Q017 | Committee members in descending rank order | **Manual-only** |
| Q018 | Same-rank members alphabetized by surname | **Manual-only** |
| Q019 | Non-NJIT entries after NJIT entries | **Manual-only** |
| Q020 | External entries include institution + city + state | **Manual-only** |
| *(structural)* | Page contains committee role labels and signature/date blocks per NJIT template | **In scope for P068 v1** — counts and template phrases only |

### Guideline paraphrase (no private text quoted)

- NJIT approval pages are expected to include committee role labels (for example dissertation
  advisor / committee member template phrases) and signature/date blocks for each approving
  member.
- P025 already warns when the approval page body is sparse; P068 narrows that gap by checking
  for **recognizable structural block patterns** rather than only line count.

---

## 6. P068 v1 Scope

### Included (PDF text layer only)

1. Detect a **unique** `APPROVAL PAGE` heading using `find_named_frontmatter_headings()`.
2. Restrict analysis to lines **below** the heading on that page (and optionally the immediate
   next page if the approval block clearly continues — v1 may stay single-page unless tests
   show wrap is common).
3. Count **role-label lines** matching curated template phrases (case-insensitive), such as:
   - `dissertation advisor`
   - `doctoral dissertation advisor`
   - `committee member`
   - `doctoral committee member`
   - `major professor`
   - `departmental graduate committee`
4. Count **signature/date structural indicators**:
   - lines containing `date:` (case-insensitive)
   - lines containing `signature` as a label token (not prose about signing)
   - lines that are predominantly underscore/dash signature blanks (`___`, `---`, ≥6 repeat)
5. Emit findings when gates pass and structural expectations fail:
   - no advisor-role label detected
   - too few combined signature/date indicators relative to role-label count
   - overall committee block count below minimum threshold

### Excluded

- Committee-member names, honorifics, titles, ranks, affiliations, institutions, cities, states
- Signature authenticity or whether signatures are present visually
- Q015–Q020 semantic ordering and completeness rules
- Advisor-before-member ordering (Q016) in v1 — deferred to v2 with y-order label check
- OCR or image analysis
- TeX source checks in v1
- Any quotation of approval-page body text in findings

### Input type

**PDF text layer only** for v1.

---

## 7. Detection Algorithm

### Step 1 — Approval page localization

```python
from njit_auditor.rules.pdf_headings import find_named_frontmatter_headings

_HEADING = "APPROVAL PAGE"
```

- Collect matches where `match.heading == "APPROVAL PAGE"`.
- **Skip** if zero matches or more than one match (ambiguous).
- **Skip** if matched page has no text blocks (image-only / flattened).

### Step 2 — Body line extraction

- Reuse the P025 pattern: `_lines_below_heading(page, "APPROVAL PAGE")`.
- Normalize each line with `normalize_heading_text()` for matching.
- Exclude the heading line itself.
- Drop lines shorter than 3 characters after normalization.

### Step 3 — Role-label detection

For each body line, test against compiled regexes built from the curated phrase list.
A line is a **role-label hit** when it matches a phrase as a whole-line or leading-clause
pattern (phrase must appear in the first ~60 characters to avoid matching body prose).

Record:

- `role_label_count`
- `advisor_label_present` (boolean; any advisor-pattern hit)
- `role_label_y_positions` (numeric y-coordinates only; no text stored in findings)

### Step 4 — Signature/date indicator detection

For each body line:

- `date_label_hit` if line matches `^\s*date\s*:` or contains `date:` as a field label
- `signature_label_hit` if line matches `^\s*signature\s*:?` (label use only)
- `signature_blank_hit` if ≥70% of non-space characters are `_`, `-`, or `.` and length ≥ 8

Compute:

- `signature_date_indicator_count = date_label_hits + signature_label_hits + signature_blank_hits`

### Step 5 — Gate and emit

| Gate | Threshold | If fail |
|---|---|---|
| Unique approval heading | exactly 1 | skip silently |
| Body lines below heading | ≥ `MIN_BODY_LINES = 4` | skip silently |
| Role-label lines | ≥ `MIN_ROLE_LABELS = 2` | skip silently (sparse/ambiguous template) |

Emit at most **one finding per issue type per page**:

1. **`approval_page_advisor_role_label_missing`** when `advisor_label_present` is false.
2. **`approval_page_signature_blocks_sparse`** when
   `signature_date_indicator_count < max(2, role_label_count)` (at least two indicators,
   and not fewer than role-label count).
3. **`approval_page_committee_blocks_sparse`** when `role_label_count < MIN_ROLE_LABELS`
   **after** passing the MIN_BODY_LINES gate but structural pattern still looks incomplete
   (optional third check; may be folded into sparse signature if redundant — implementer
   should keep ≤2 issue types active in v1 to limit noise).

### Confidence scoring

| Condition | `confidence` |
|---|---|
| ≥3 role labels and ≥3 signature/date indicators | `high` |
| 2 role labels and 2 indicators | `medium` |
| Gate-pass with borderline counts | `low` |

### Privacy invariant

Finding `details` may include only: page number, counts, booleans, y-positions (rounded pt),
`issue_type`, `confidence`, `triage_tier`, `source_q_rule_ids` (e.g. `"Q013"` structural
extension note). **Never** include line text, names, or institution strings.

---

## 8. Issue Types

| Issue type | Severity | Meaning |
|---|---|---|
| `approval_page_advisor_role_label_missing` | warning | Unique approval page detected but no advisor-role template phrase found |
| `approval_page_signature_blocks_sparse` | warning | Role labels present but insufficient signature/date structural indicators |
| `approval_page_committee_blocks_sparse` | advisory (optional v1) | Approval body present but fewer than minimum role-label blocks |

`triage_tier`: `medium` for all issue types.

---

## 9. Finding Fields

### Allowed fields (privacy-safe)

| Field | Type | Description |
|---|---|---|
| `page_number` | string | Approval page index |
| `issue_type` | string | One of the issue types above |
| `role_label_count` | string (int) | Count of template role-label lines |
| `advisor_label_present` | string (`"true"`/`"false"`) | Whether advisor phrase detected |
| `signature_date_indicator_count` | string (int) | Count of date/signature/blank indicators |
| `date_label_count` | string (int) | Sub-count for date labels |
| `signature_label_count` | string (int) | Sub-count for signature labels |
| `signature_blank_count` | string (int) | Sub-count for underscore blanks |
| `confidence` | string | `low` / `medium` / `high` |
| `triage_tier` | string | `medium` |
| `source_q_rule_ids` | string | `"Q013"` (structural extension; not a full Q015–Q020 claim) |

### Explicitly excluded

- Committee-member names or initials
- Honorifics (`Dr.`, `Prof.`, etc.) tied to identifiable text
- Institution, city, state strings
- Signature images or OCR output
- Full line text or approval-page prose
- EF comment text

---

## 10. Conservative Skip Conditions

| Condition | Action |
|---|---|
| No `APPROVAL PAGE` heading detected | Skip silently |
| Multiple `APPROVAL PAGE` headings | Skip silently |
| Image-only / no text blocks on approval page | Skip silently |
| Fewer than 4 body lines below heading | Skip silently |
| Fewer than 2 role-label hits after phrase scan | Skip silently (template too sparse/nonstandard) |
| Approval page text dominated by EF annotation artifacts | Skip if >50% lines are single-token noise (reuse P025 substantial-line heuristic) |
| Flattened PDF with collapsed spacing making phrase detection unreliable | Skip silently |

---

## 11. False-Positive and False-Negative Risks

### False positives

- Department templates use non-curated advisor phrases (`Research Advisor`, `Thesis Supervisor`)
  → mitigated by expandable phrase list and skip gates.
- Signature lines rendered as images → counted as missing indicators (acceptable FN bias).
- Combined advisor/committee lines in one paragraph → under-count role labels.

### False negatives

- Correct pages using only visual signature lines without text-layer `Date:` labels.
- Templates that omit explicit `Dissertation Advisor` wording but include compliant structure.
- Multi-page approval blocks where v1 single-page scan misses continuation (v2 cross-page).

### Operational note

Zero findings on the five-PDF evaluation set would **not** prove compliance — same limitation
documented for P065/P066/P067 when detection gates skip files.

---

## 12. Synthetic Test Plan

Minimum **12** tests in `tests/test_p068_approval_page_committee_blocks.py`:

| # | Scenario | Expected |
|---|---|---|
| 1 | No approval page in document | No findings |
| 2 | Unique approval page with advisor label + 3 role labels + date/signature indicators | No findings |
| 3 | Approval page with committee labels but no advisor phrase | `approval_page_advisor_role_label_missing` |
| 4 | Advisor label present but no date/signature indicators | `approval_page_signature_blocks_sparse` |
| 5 | Only 1 role label and 1 body line (below gates) | No findings |
| 6 | Multiple `APPROVAL PAGE` headings | No findings |
| 7 | Image-only approval page (no text blocks) | No findings |
| 8 | Approval page with underscore signature blanks counted as indicators | No sparse finding when counts satisfy gate |
| 9 | `Major Professor` variant phrase counts as advisor label | No advisor-missing finding |
| 10 | Non-approval page containing word `committee` in body prose | No findings (page not selected) |
| 11 | Privacy: triggered finding details contain no line text or name-like tokens | Pass |
| 12 | Heading present; body is 3 substantial lines but zero role labels (below MIN_ROLE_LABELS gate) | No findings |

Optional extras:

- Date label without colon variant (`Date __________`)
- Continuation page deferred test stub (document skip behavior)

Synthetic fixtures must use placeholder names only (`Advisor Placeholder`, `Member Example`).

---

## 13. Current-Dataset Evaluation Plan

After implementation:

1. Run P068-only extraction on the five evaluation PDFs (same set as
   `docs/evaluation/current_auditor_after_p067_evaluation.md`).
2. Record per-file: approval heading detected (Y/N), role-label count, indicator count,
   P068 finding count by issue type.
3. Produce `docs/evaluation/p068_current_dataset_evaluation.md` (aggregate counts only).
4. Optionally refresh full aggregate snapshot if P068 findings are non-zero.

**Privacy:** No approval-page text, names, or EF comments in the evaluation doc.

---

## 14. Implementation Checklist

| Item | Path / action |
|---|---|
| New module | `src/njit_auditor/rules/pdf_approval_page_committee_blocks.py` |
| Public entry | `check_pdf_approval_page_committee_blocks(pdf_document) -> list[AuditFinding]` |
| Wire into runner | `src/njit_auditor/audit_runner.py` — import + call in `collect_pdf_layout_findings()` |
| Evaluation category | `src/njit_auditor/evaluation.py` — `"P068": "committee_approval_page"` |
| Inventory entry | `data/processed/rules/project_added_rules.json` — add P068 stub after implementation |
| Tests | `tests/test_p068_approval_page_committee_blocks.py` (≥12) |
| Synthetic validation doc | `docs/evaluation/p068_approval_page_committee_blocks_synthetic_validation.md` |
| Current-dataset eval doc | `docs/evaluation/p068_current_dataset_evaluation.md` |
| Status refresh | `docs/status/current_project_state_and_next_steps.md` |
| Validation | `ruff check .`, `mypy src`, `python -m pytest` |

---

## 15. Recommendation

**Ready for implementation** as a focused PDF rule PR after this scope doc merges.

Suggested implementation PR:

- Branch: `rules/p068-approval-page-committee-blocks`
- Title: `Implement P068 approval page committee block structural check`
- Scope guard: implement only v1 checks listed above; do not expand into Q015–Q020 semantics.

### Caveats

- EF overlap improvement is **category-level** only; page-level EF intent is not guaranteed to match.
- Template phrase list will need maintenance as additional NJIT department variants are discovered.
- Shared front-matter heading detection improvements remain a separate, high-value refinement.
