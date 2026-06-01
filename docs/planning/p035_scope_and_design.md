# P035 Scope and Design

- **Date:** 2026-06-01
- **Status:** Implemented
- **Baseline main:** `b19c452` (P001–P035 implemented; status refresh PR #84; P035 implementation PR #83 `c31dfd5`)
- **Author:** Design/scoping only; no detector code in this document

## Current state

| Area | State |
|------|--------|
| P-rules | **35/35** implemented (`P001`–`P035`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented |
| Manual-only framing | **9** `checkability=manual` + **57** automatable `not_implemented` |
| Figure/table caption text | **P017** — punctuation/case on caption lines only |
| Figure/table body layout | **P035** — text-layer body centering and caption placement (v1; image floats skipped) |
| PDF geometry | Text blocks + bboxes via `pdf_layout.py`; **image blocks not yet extracted** (TODO in loader) |
| Reusable helpers | `detect_caption_lines()` in `pdf_captions.py`; text-area centering from `pdf_headings.py` / `pdf_margins.py` |

Remaining automatable clusters (from status/coverage docs) include figure/table centering and caption placement (Self-Assessment Sheet), dedication layout (Q033–Q034), front-matter exact heading phrases (Q013, Q021, Q036, Q047, Q061, Q070 — partially addressed by P014/P030/P031), and LoT/LoF inter-entry spacing (Q058, Q077).

---

## Candidate comparison

### Candidate A — Figure/table body centering and caption placement (recommended)

| Field | Detail |
|-------|--------|
| **Source basis** | Self-Assessment Sheet (figure/table centering; table title above table); `docs/status/current_project_state_and_next_steps.md` §4A; `docs/status/rule_coverage_audit.md` (useful-but-heuristic table) |
| **Expected rule** | **P035** — PDF figure/table body layout |
| **Module** | `src/njit_auditor/rules/pdf_figure_table_layout.py` |
| **Finding types** | `figure_body_not_centered`, `table_body_not_centered`, `table_caption_not_above_body`, `figure_caption_not_below_body`, `insufficient_body_signal` (informational skip — no warning) |
| **Risk / noise** | **Medium** — image-only figures lack body bbox; dense pages may mis-group blocks; conservative skips required |
| **Privacy** | **Low** — geometry and caption labels only; no caption body text beyond existing P017 previews |
| **Tests** | Synthetic `PdfDocument` fixtures in `tests/test_pdf_rules.py`; centered/off-center table blocks; caption above/below ordering |
| **Five-PDF impact** | **Low–moderate** initially — text-heavy tables may flag; image figures likely skipped until image-block support exists |
| **Why P035?** | Fills the clearest **new** automatable gap after P034; extends existing caption/geometry stack without overlapping P017/P018/P030–P032 |

### Candidate B — Dedication page centering and italic (Q033–Q034)

| Field | Detail |
|-------|--------|
| **Source basis** | Q033, Q034; optional front-matter section |
| **Expected rule** | P035 — PDF dedication page layout |
| **Module** | `src/njit_auditor/rules/pdf_dedication_page.py` |
| **Finding types** | `dedication_text_not_centered`, `dedication_text_not_italic` |
| **Risk / noise** | **High** — dedication is optional; page detection fragile; italic metadata often absent in PDF text layer |
| **Privacy** | **Medium** — dedication prose must not appear in findings |
| **Tests** | Synthetic dedication page with centered/offset blocks |
| **Five-PDF impact** | **Unknown/low** — section may be absent on most evaluation PDFs |
| **Why not P035?** | Narrow optional section; weak font-style signal; better as later front-matter bundle after dedicated page detection exists |

### Candidate C — Front-matter exact heading phrase enforcement (Q013, Q021, Q036, Q047, Q061, Q070)

| Field | Detail |
|-------|--------|
| **Source basis** | Q013, Q021, Q036, Q047, Q061, Q070 exact heading requirements |
| **Expected rule** | P035 or P014 refinement |
| **Module** | Extend `pdf_headings.py` or `pdf_toc_continued_headings.py` |
| **Finding types** | `exact_heading_phrase_missing`, `continued_heading_not_bold_centered` |
| **Risk / noise** | **Medium** — overlaps **P014** (layout), **P030** (continued text presence), **P031** (column headers); incremental value is bold/centering on continued headings only |
| **Privacy** | **Low** |
| **Tests** | Extend existing P014/P030 fixtures |
| **Five-PDF impact** | **Low** — P014 already at 0 on current snapshot after centering fix |
| **Why not P035?** | Mostly refinement of existing rules; does not open a new guideline area; better as targeted P014/P030 hardening PR |

### Candidate D — LoT/LoF inter-entry double spacing (Q058, Q077)

| Field | Detail |
|-------|--------|
| **Source basis** | Q058, Q077 — visible double spacing between consecutive list entries |
| **Expected rule** | P035 — PDF list inter-entry spacing |
| **Module** | `src/njit_auditor/rules/pdf_toc_list_entry_spacing.py` |
| **Finding types** | `list_entry_spacing_too_tight` |
| **Risk / noise** | **High** — complements P032 (intra-entry) but gap measurement between entries is ambiguous with wrapped lines |
| **Five-PDF impact** | **Unknown** — likely noisy until entry segmentation improves |
| **Why not P035?** | TOC/List cluster already has P018/P024/P030–P032; add only after figure/table gap or as P036 |

### Ranking

1. **A — Figure/table body layout** (recommended P035)
2. **C — Front-matter exact headings** (refinement, not new rule)
3. **D — LoT/LoF inter-entry spacing** (follow-on TOC/List work)
4. **B — Dedication layout** (optional section, high skip/FP rate)

---

## Selected P035 scope

### Rule title

**P035 — PDF figure/table body layout (centering and caption placement)**

### Source basis

- Self-Assessment Sheet checklist (figure/table centering; table titles above tables)
- Project gap list: `docs/status/current_project_state_and_next_steps.md` §4A
- Builds on caption detection in `pdf_captions.py` (P017); does **not** duplicate P017 punctuation/case checks

### Scope included

1. **Pages:** Body/chapter pages only — skip TOC, LoT, LoF, references, and named front-matter pages (reuse `_page_context()` from `pdf_captions.py`).
2. **Caption anchoring:** Reuse `detect_caption_lines()` to find `Figure N` / `Table N` caption lines on body pages.
3. **Body block inference (conservative):**
   - On the same page as the caption, collect non-caption text blocks (or future image bboxes) within a vertical window adjacent to the caption.
   - Require minimum block area/line count before emitting layout findings.
   - **Skip** when no confident body block is found (image-only figures, sparse text layer).
4. **Horizontal centering:** Compare union bbox horizontal center to **text-area center** (same approach as P014: `LEFT_MARGIN_PT` / `RIGHT_MARGIN_PT` from `pdf_margins.py`), with tolerance ≈12–18 pt.
5. **Caption placement:**
   - **Table:** caption line must be **above** inferred table body block (smaller `y0` in page coordinates).
   - **Figure:** caption line must be **below** inferred figure body block.
6. **Findings:** One warning per `(page, caption_number, issue_type)`; details include `caption_type`, `issue_type`, page number, coarse offset metrics — **no dissertation body text**.

### Scope excluded

- Caption punctuation, title case, or terminal period (P017)
- TOC/LoT/LoF list entry formatting (P018, P024, P030–P032)
- Image-block extraction / vector graphics (defer until `pdf_layout.py` image support lands)
- Multi-page floats, subfigures, sideways tables, full-width landscape pages
- Equation numbering, references consistency, biographical/dedication front matter
- TeX-side `\begin{figure}` / `\begin{table}` environment checks (separate future TeX rule if needed)
- Reporting triage rollup (add only if volume warrants, post-implementation)

### Expected module path

`src/njit_auditor/rules/pdf_figure_table_layout.py`

Public entry point: `check_pdf_figure_table_layout(pdf_document: PdfDocument) -> list[AuditFinding]`

### CLI / report wiring

- **CLI:** Add call in `src/njit_auditor/cli.py` PDF audit path **after** `check_pdf_captions(pdf_doc)` (layout depends on caption detection).
- **Inventory:** Append P035 entry to `data/processed/rules/project_added_rules.json` at implementation time.
- **Reports:** Standard JSON/Markdown finding output; no new triage rollup in v1 unless finding volume exceeds ~50 per document in evaluation.
- **Evaluation mapping:** Add `"P035": "figure_format"` or `"table_format"` in `src/njit_auditor/evaluation.py` based on `caption_type` in details.

### Expected tests

| Test | Purpose |
|------|---------|
| Centered table body synthetic page | No `table_body_not_centered` finding |
| Off-center table body | Emits `table_body_not_centered` |
| Table caption below body | Emits `table_caption_not_above_body` |
| Figure caption above body | Emits `figure_caption_not_below_body` |
| Image-only / no body blocks | No layout findings (skip) |
| TOC page with figure-like line | Skipped via context |
| Inventory wiring | P035 present in `project_added_rules.json` after implementation |

Follow patterns in `tests/test_pdf_rules.py` (P030–P034 synthetic fixtures).

### Privacy constraints

- Do **not** quote caption body text, figure labels beyond `Figure N` / `Table N`, or any dissertation prose in findings or committed evaluation docs.
- Reuse P017-style line previews only if already established; prefer numeric offsets and `issue_type` only for P035 v1.
- Evaluation write-ups: aggregate counts only.

### Acceptance criteria

1. P035 registered in `project_added_rules.json` with `implementation_status=implemented`.
2. CLI PDF audit invokes `check_pdf_figure_table_layout`.
3. Synthetic tests cover centering and caption-above/below for text-layer table/figure blocks.
4. No findings on synthetic “compliant” fixtures.
5. Ambiguous/image-only cases produce **zero** findings (conservative skip).
6. `ruff check .`, `mypy src`, full `pytest` pass.
7. No changes to P001–P034 detector behavior.

### Known false-positive risks

| Risk | Mitigation |
|------|------------|
| Side-by-side subfigures | Skip when multiple body clusters compete |
| Full-width tables intentionally left-aligned | Require fraction of body width vs text area before centering check |
| Caption on separate page from float | Same-page-only in v1 |
| Headers/footers near caption | Exclude margin zones and page-number lines |
| Image-only figures | Skip until image bbox extraction exists |

### Generated outputs

After implementation, **rerun five-PDF evaluation locally** into a new gitignored path (e.g. `data/evaluation/generated/current_auditor_after_p035/`) and add `docs/evaluation/p035_current_dataset_evaluation.md` — **do not commit** generated JSON/MD under `data/evaluation/generated/`.

---

## Implementation status (completed PR #83)

1. ✅ `pdf_figure_table_layout.py` with body-block inference helpers.
2. ✅ CLI + `project_added_rules.json` + `evaluation.py` category map wired.
3. ✅ Synthetic tests; full validation (**424 pytest**).
4. ✅ Local four-PDF subset evaluation doc: `docs/evaluation/p035_current_dataset_evaluation.md` (not canonical five-PDF aggregate).
5. ✅ Status/docs refresh through PR #84 (`b19c452`).

Full five-PDF canonical P001–P035 rerun remains optional future work (gitignored `current_auditor_after_p035/`).

---

## Validation plan

| Step | Command |
|------|---------|
| Unit/synthetic | `python -m pytest tests/test_pdf_rules.py -k p035 -q` |
| Full suite | `ruff check . && mypy src && python -m pytest` |
| Local eval (post-impl) | Five-PDF audit script → gitignored output path |

---

## Privacy notes

- P035 is geometry-first; findings must remain aggregate and metadata-only.
- Do not copy evaluation PDF content into committed docs.
- Author names, titles, committee names, and annotation text remain out of scope for findings and documentation.

## Generated-output safety

- All audit JSON/MD artifacts stay under gitignored `data/evaluation/generated/`.
- This scoping PR commits **only** planning/status documentation.
