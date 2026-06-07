# GUI Scope and Design — NJIT Thesis Auditor

- **Date:** 2026-06-07
- **Baseline commit:** `fde8f9d` (PR #213 — TeX/ZIP web upload UI)
- **Validation at design time:** ruff, mypy, **830 pytest** passed (after job TTL/docs PR)
- **Status:** Design reference — FastAPI web UI is **implemented** on `main`; this doc tracks scope, phases, and follow-ups
- **Related:** `docs/web_gui_mvp.md` (FastAPI operations guide)

---

## 1. Purpose and non-goals

### Purpose

Make the NJIT thesis auditor easier to use through a **local web/GUI interface** that:

- Accepts a dissertation PDF, TeX source, or LaTeX project archive
- Runs the same audit engine as the CLI
- Presents a **polished, organized, privacy-safe report** with triage-first summaries
- Encourages adoption by graduate students and reviewers without CLI expertise

### Non-goals (v1)

| Non-goal | Rationale |
|---|---|
| Cloud upload or multi-user persistent storage | Private dissertation content must stay local |
| External document analysis services | Offline-by-default; no paid APIs |
| AI text generation over private body text | Risk of leakage and hallucination; out of scope unless explicitly designed later with a written privacy policy |
| OCR by default | Aligns with PDF text-layer-only audit philosophy |
| Official NJIT endorsement branding | Research prototype only |
| Replacing CLI | CLI remains the canonical automation interface |

### Design principles

1. **Privacy-first:** aggregate metadata in UI; no dissertation body text by default
2. **Correctness:** GUI is a thin wrapper over audited backend functions — no duplicate rule logic
3. **Honest labeling:** heuristic findings labeled “review needed,” not “defect confirmed”
4. **Local-only processing:** no analytics, no external network calls during audit (URL fetch is optional and already SSRF-guarded; v1 polished UI should treat it as advanced/opt-in)

---

## 2. Current backend contract

### CLI audit modes (`njit-audit`)

| Command | Input | Rules | Output |
|---|---|---|---|
| `njit-audit pdf <path>` | Single `.pdf` | **P011–P061** (full PDF layout audit) | Rich console report; optional `--json-out` / `--md-out` |
| `njit-audit tex <main.tex>` | Single `.tex` (recursive `\input`/`\include`) | **P001–P010** TeX source checks | Console + `--json-out` / `--md-out` |
| `njit-audit audit <path>` | Single `.pdf` | Legacy P001–P003 subset | Console report |
| `njit-audit pdf-comments extract/clean` | Single `.pdf` | Annotation metadata / clean copy | JSON/MD or cleaned PDF |

**ZIP / project directory:** Not implemented in CLI today. `load_tex_project()` in
`latex_loader.py` accepts a resolved main `.tex` path and recursively loads referenced files
from the filesystem. A future GUI must add **safe ZIP extraction** plus main-file detection.

### Programmatic entrypoints

| Module | Role | Reuse for GUI |
|---|---|---|
| `cli.py` → `pdf()` | Canonical P011–P061 PDF pipeline | **Refactor target:** extract shared `run_pdf_audit_full()` used by CLI and web |
| `audit_runner.py` → `run_pdf_audit_full()` | Python API without Typer | **Shared entrypoint** — P011–P061; used by CLI (`collect_pdf_layout_findings`) and web UI |
| `cli.py` → `collect_tex_findings()` | TeX P001–P010 | Wrap for GUI TeX mode |
| `report_outputs.py` | JSON/Markdown serialization + triage rollups | **Direct reuse** |
| `rule_loader.py` | Rule definitions with `remediation` text | **Reuse for polished comments** |
| `web_app.py` | FastAPI upload UI (PDF, TeX, ZIP) | **Implemented** |

### Expected inputs (current + proposed)

| Input type | Supported today | Proposed v1 GUI |
|---|---|---|
| Single PDF | CLI, web upload, URL fetch, built-in samples | Yes |
| Single `.tex` | CLI, web upload | Yes (upload + temp dir) |
| LaTeX project directory | CLI if path known | Indirect via ZIP upload |
| `.zip` LaTeX project | Web upload | Yes (safe extract + main `.tex` detection) |

### Current outputs

#### JSON report schema (`audit_findings_to_json_dict`)

```json
{
  "metadata": {
    "total_findings": 0,
    "counts_by_severity": {"PASS": 0, "WARNING": 0, "FAIL": 0},
    "counts_by_rule_id": {"P011": 0},
    "counts_by_category": {"margin_or_overflow": 0},
    "generated_at": "ISO-8601",
    "note": "Findings are heuristic signals and require human review."
  },
  "grouped_summary": {
    "high_volume_rules": [],
    "by_rule_issue_type": {},
    "p011_margin_triage": {},
    "p013_triage": {},
    "p026_font_triage": {},
    "p012_annotation_triage": {}
  },
  "findings": [
    {
      "rule_id": "P011",
      "severity": "WARNING",
      "message": "...",
      "page": 2,
      "details": {"issue_type": "...", "...": "truncated to 120 chars"}
    }
  ]
}
```

**Privacy sanitization already applied:** `_sanitize_details()` truncates detail values to
120 characters in JSON output.

#### Markdown report

- Summary table (totals by severity)
- Repeated Findings Summary (`high_volume_rules`)
- P011 / P012 / P013 / P026 triage sections (when present)
- Full raw findings list

#### Triage rollups (reporting-only; detection unchanged)

| Key | Rule | Contents |
|---|---|---|
| `p011_margin_triage` | P011 | Side counts, overflow patterns, compact page ranges, `triage_note` |
| `p013_triage` | P013 | Position/style counts, multi-candidate pages, pattern page ranges |
| `p026_font_triage` | P026 | Family/size issue counts, dominant labels, page ranges |
| `p012_annotation_triage` | P012 | Annotation type counts and pages (no comment body text) |

### Existing web MVP (`web_app.py`)

Already implements:

- PDF upload with extension, size, and `%PDF` magic-byte validation
- Background audit thread + job status polling (`/audits/{id}/status`)
- Results page with finding list + high-volume rule summary
- JSON/Markdown download
- Optional public PDF URL fetch (SSRF-safe via `web_url_fetch.py`)
- Built-in sample PDF dropdown (`web_samples.py`)
- Runtime under gitignored `.runtime/web_audits/`

**Gaps vs target GUI:**

- ~~No TeX or ZIP upload~~ — **Done** (PR #213)
- No category/severity summary cards
- No P011/P013/P026 triage-first panels (only `high_volume_rules` subset)
- No rule/category/page filters
- ~~No polished comment templates~~ — **resolved** (`polished_comments.py`, `report_view.py`)
- ~~`audit_runner.py` not aligned with CLI P055–P061~~ — **resolved** (shared `run_pdf_audit_full` / `collect_pdf_layout_findings`)
- No temp-file TTL cleanup policy documented

### Reuse vs thin wrapper needs

| Component | Reuse as-is | Thin wrapper needed |
|---|---|---|
| `audit_findings_to_json_dict` | Yes | — |
| `write_markdown_report` | Yes | — |
| `build_grouped_summary` + triage builders | Yes | View-model mapper for UI cards |
| `run_pdf_audit_full` / CLI `pdf()` | **Done** | Shared via `collect_pdf_layout_findings()` |
| `run_audit_for_uploaded_file()` | **Done** | Web uses for PDF; TeX/ZIP backend-ready |
| `collect_tex_findings` | Yes | Upload handler + optional linters flag |
| ZIP handling | **Done** (`safe_extract_zip`, `detect_main_tex`) | Web UI + dispatcher |
| Job TTL cleanup | **Done** (`cleanup_expired_jobs`, `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS`) | Default 24 h |
| Polished comments | No | New template layer from `rule_loader` + finding metadata |
| Report view DTOs | **Done** | `report_view.py` + minimal web results integration |
| Polished comments | **Done** | `polished_comments.py` (privacy-safe templates) |

---

## 3. Recommended GUI architecture

### Framework comparison

| Option | Pros | Cons | Fit for this repo |
|---|---|---|---|
| **Streamlit** | Fast local prototype; pure Python UI | Rerun model; awkward job/progress UX; duplicates existing FastAPI work | Good greenfield; **poor fit given existing MVP** |
| **Gradio** | Simple upload/demo | ML-demo oriented; limited report tables/filters | Low |
| **NiceGUI** | Python-native; good local apps; reactive components | New stack; no reuse of `web_app.py` tests | Reasonable greenfield alternative |
| **FastAPI + Jinja2** (current) | Already shipped; TestClient tests; download routes; background jobs | Template UX less polished than SPA | **Best fit — evolve in place** |
| **FastAPI + React** | Rich filtering, component reuse | Node build chain; higher maintenance | Phase 3+ if UX demands SPA |
| **Dash** | Strong tables/charts | Heavy; Plotly-centric | Low |
| **PySide/PyQt** | True desktop offline | Packaging complexity; no browser access | Out of scope for “local web UI” goal |

### Recommended v1 path

**Evolve the existing FastAPI + Jinja2 web application** (`web_app.py`), not a greenfield
Streamlit/NiceGUI rewrite.

Rationale:

1. MVP already deployed with **25+ web tests** (`tests/test_web_app.py`)
2. Upload validation, job model, SSRF-safe URL fetch, and download routes exist
3. Aligns with README and `docs/web_gui_mvp.md`
4. Avoids maintaining two GUI stacks

**UI enhancement strategy (no framework change):**

- Phase 1–2: Improve Jinja2 templates + minimal CSS; optional **HTMX** for filter/poll without React
- Phase 3+: Revisit React/Vue only if interactive page-preview requirements exceed template limits

**NiceGUI fallback:** If FastAPI template iteration proves too slow for page-linked preview
(Phase 3), prototype page viewer in NiceGUI as a **separate optional entrypoint** — not v1 default.

---

## 4. Proposed v1 user flow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────────┐
│ Select input│───▶│ Validate type│───▶│ Run audit   │───▶│ Triage dashboard │
│ PDF/TeX/ZIP │    │ size, magic  │    │ (background)│    │ + filtered table │
└─────────────┘    └──────────────┘    └─────────────┘    └────────┬─────────┘
                                                                     │
                                     ┌───────────────────────────────┘
                                     ▼
                            ┌─────────────────┐
                            │ Export JSON/MD  │
                            └─────────────────┘
```

### Step-by-step

1. **Landing page** — three input methods (keep existing): file upload, optional public URL (advanced), built-in samples (dev/demo only)
2. **File type detection** — extension + magic bytes (PDF `%PDF`, ZIP `PK\x03\x04`, TeX text heuristic)
3. **Validation** — max size (default 50 MB, env-configurable), filename sanitization, reject unsupported types
4. **Preparation** — PDF → temp path; TeX → temp `.tex`; ZIP → safe extract → detect `main.tex`
5. **Audit execution** — background task; status: `pending → running → complete | failed`
6. **Progress** — poll `/audits/{id}/status`; show spinner + elapsed time; no partial findings stream in v1
7. **Summary dashboard**
   - Total findings card
   - Severity breakdown (PASS / WARNING / FAIL)
   - Category bar chart or table
   - Rule breakdown (top N + “show all”)
   - **Triage-first panels:** P011, P013, P026 (and P012 when present) above raw table
8. **Findings table** — columns: rule, category, page, severity, issue type, polished comment; filters by rule/category/page/severity
9. **Polished comments** — template-generated from rule remediation + finding metadata (see §7)
10. **Export** — download JSON and Markdown (existing routes)

---

## 5. Upload correctness requirements

### File type matrix

| Extension | Magic / check | Audit mode | v1 |
|---|---|---|---|
| `.pdf` | `%PDF` header | PDF P011–P061 | Yes (exists) |
| `.tex` | UTF-8 text; contains `\documentclass` | TeX P001–P010 | Add |
| `.zip` | `PK\x03\x04` | Extract → TeX | Add (new utility) |
| Other | — | Reject with clear error | Yes |

### Safety requirements

| Requirement | Implementation notes |
|---|---|
| Work only under temp/runtime dir | `RUNTIME_DIR / job_id /`; never audit user-supplied absolute paths |
| Sanitize filenames | Existing `_SAFE_NAME_RE` pattern; strip path components |
| Max file size | Enforce before write; default 50 MB (`NJIT_AUDITOR_WEB_MAX_UPLOAD_MB`) |
| Max ZIP uncompressed size | Proposed: 200 MB total extracted per job |
| Max ZIP file count | Proposed: 500 files |
| Zip-slip protection | Reject entries with `..`, absolute paths, or resolved path outside target dir |
| Allowed ZIP extensions | `.tex`, `.bib`, `.bst`, `.cls`, `.sty`, `.png`, `.jpg`, `.jpeg`, `.pdf` (no `.exe`, `.sh`, symlinks) |
| Main `.tex` detection | Priority: (1) single `\documentclass` file at shallowest depth, (2) `main.tex`, (3) largest `\documentclass` file; fail if ambiguous |
| Malformed PDF | Catch `FileDataError` / `AuditError`; surface user-safe message |
| Temp cleanup | Delete job dir on completion after TTL (proposed: 24 h) + immediate delete on validation failure |
| Never commit uploads | `.runtime/` gitignored; tests use `tmp_path` |
| No OCR | Do not add OCR dependencies in GUI path |

### ZIP support (not implemented today)

Define `safe_zip_extract(archive: Path, dest: Path) -> ExtractResult` with the limits above.
CLI and GUI both call this utility when ZIP support lands.

---

## 6. Report display design

### Information hierarchy

1. **Executive summary** — totals, severity, top categories
2. **High-volume triage** — P011, P013, P026 panels (expand P012 when annotations present)
3. **Grouped summary table** — `high_volume_rules` from JSON
4. **Filterable findings table** — all raw findings with polished comment column
5. **Export actions** — JSON / Markdown

### Filters (v1)

| Filter | Source field |
|---|---|
| Rule | `finding.rule_id` |
| Category | `map_finding_rule_to_category(rule_id, details)` |
| Page | `finding.page` |
| Severity | `finding.severity` |
| Issue type | `finding.details.issue_type` |

### Triage-first display

For P011/P013/P026, render the existing rollup objects directly:

- Show `triage_note` / `triage_tier` prominently
- Compact page ranges (already computed)
- Collapse raw per-page findings under “show details”

### Finding card fields

| Field | Source | Show in v1 |
|---|---|---|
| Rule ID | `finding.rule_id` | Yes |
| Category | mapped category | Yes |
| Page | `finding.page` | Yes |
| Severity | `finding.severity` | Yes |
| Issue type | `details.issue_type` | Yes |
| Concise explanation | polished template | Yes |
| Remediation | `rule_loader` remediation + `details.suggested_fix` | Yes |
| Confidence / triage tier | `details.confidence`, `details.triage_tier` | When present |
| Raw `message` | finding.message | Secondary (collapsible) |
| `details` blob | sanitized details | Advanced collapsible only |

### Privacy defaults

- **Do not show** `observed_summary` or other extracted text snippets in prominent UI by default
- **Do not show** annotation comment text (P012 already avoids body text in triage)
- Optional “show extracted text context” — **disabled in v1**; requires explicit privacy policy before enabling

---

## 7. Polished comments design

### Generation rules

1. Load static rule metadata from `data/processed/rules/project_added_rules.json` via `rule_loader`
2. Build comment from: `rule_id`, `issue_type`, `severity`, `page`, `triage_tier`, `confidence`, `suggested_fix` (if present)
3. **Never** insert dissertation body text, titles, author names, or captions
4. Prefix heuristic findings: **“Review needed:”** not “Error:” or “Violation:”
5. Append standard disclaimer: “Heuristic signal — confirm against NJIT guidelines manually.”

### Template shape

```
Review needed: [category/rule summary] on page [N].
Issue type: [issue_type]. [rule-specific sentence from remediation map].
Confidence: [confidence/triage_tier if present].
```

### Representative examples (metadata-only)

#### P011 — margin overflow

- **Inputs:** `issue_type=margin_boundary_violation`, `side=left_margin`, page 42
- **Polished comment:** “Review needed: Possible text crossing the left margin on page 42. Check that body text and headings respect the 1-inch margin requirement. Heuristic signal — confirm against NJIT guidelines manually.”

#### P013 — page number candidate

- **Inputs:** `issue_type=page_number_candidate`, `position_type=bottom_center`, `confidence=medium`, page 15
- **Polished comment:** “Review needed: A page-number-like token was detected at the bottom center of page 15. Verify page numbering placement and style match NJIT requirements. Heuristic signal — confirm against NJIT guidelines manually.”

#### P026 — font compliance

- **Inputs:** `issue_type=possible_body_font_family_issue`, `confidence=medium`, page 8
- **Polished comment:** “Review needed: Body text on page 8 may not use the expected Times New Roman family. Compare embedded fonts against NJIT font requirements. Heuristic signal — confirm against NJIT guidelines manually.”

#### P030 — TOC continued headings

- **Inputs:** `issue_type=missing_continued_heading` (or equivalent), page 12, list type TOC
- **Polished comment:** “Review needed: A multi-page TABLE OF CONTENTS may be missing a continued heading on page 12. Verify ‘TABLE OF CONTENTS (Continued)’ appears on continuation pages. Heuristic signal — confirm against NJIT guidelines manually.”

#### P033 — title consistency

- **Inputs:** `issue_type=title_page_mismatch` (representative), page 1
- **Polished comment:** “Review needed: Title-page metadata may be inconsistent across detected title regions on page 1. Manually verify the title, degree line, and author block match NJIT front-matter requirements. Heuristic signal — confirm against NJIT guidelines manually.”

#### P034 — copyright page

- **Inputs:** `issue_type=copyright_author_not_found` (representative), page 2
- **Polished comment:** “Review needed: A copyright page was detected on page 2 but author metadata could not be verified automatically. Confirm the copyright block includes the required author and year format. Heuristic signal — confirm against NJIT guidelines manually.”

#### P061 — LoT/LoF cross-page entry ordering

- **Inputs:** `issue_type=lof_cross_page_entry_numbers_not_nondecreasing`, `triage_tier=medium`, pages 17–18
- **Polished comment:** “Review needed: List of Figures entry numbers may not be non-decreasing across pages 17–18. Verify cross-page numbering continuity in the LoF. Heuristic signal — confirm against NJIT guidelines manually.”
- **Zero-finding case:** GUI should not invent comments; show triage panel note: “No qualifying multi-page LoT/LoF sequences with comparable entries were detected — compliance not verified.”

---

## 8. Correctness and testing plan

### Existing coverage

- `tests/test_report_outputs.py` — JSON schema, triage rollups, Markdown sections
- `tests/test_web_app.py` — upload validation, job lifecycle, downloads, URL/sample paths

### Additional tests required for GUI v1

| Test area | Example test name | Assertion |
|---|---|---|
| PDF upload | `test_gui_pdf_upload_success` | Job completes; JSON schema keys present |
| TeX upload | `test_gui_tex_upload_success` | `.tex` triggers TeX audit; P001–P010 findings |
| Malformed PDF | `test_gui_malformed_pdf_fails_gracefully` | Job `failed`; safe error message |
| Unsupported type | `test_gui_rejects_docx` | 400; no files written |
| Oversized file | `test_gui_rejects_oversized_upload` | 413 |
| Zip-slip | `test_safe_zip_rejects_path_traversal` | Raises / rejects `../evil.tex` |
| ZIP file bomb (count) | `test_safe_zip_rejects_too_many_files` | Rejects >500 entries |
| ZIP main detection | `test_safe_zip_finds_main_tex` | Picks correct `\documentclass` file |
| JSON schema compatibility | `test_gui_json_matches_cli_schema` | GUI/CLI payloads identical shape |
| Markdown export | `test_gui_markdown_download` | Contains triage sections when rollups present |
| Triage rendering | `test_gui_renders_p013_triage_panel` | HTML includes triage counts, not body text |
| Polished comments | `test_polished_comments_exclude_body_text` | No words from synthetic fixture body |
| Temp cleanup | `test_job_dir_removed_after_ttl` | Runtime dir deleted per policy |
| Determinism | `test_synthetic_pdf_deterministic_counts` | Same fixture → same rule counts |

### Contract test (critical)

Add `test_audit_runner_matches_cli_pdf_rule_set` after unifying PDF audit entrypoints —
web and CLI must produce identical finding counts on shared synthetic fixtures.

---

## 9. Security and privacy checklist

| Control | v1 requirement | Current status |
|---|---|---|
| Local-only audit processing | No external API calls during rule execution | Met |
| No analytics / telemetry | No third-party JS trackers | Met (templates) |
| No persistent user storage | Job dirs ephemeral under `.runtime/` | Partial — add TTL cleanup |
| Gitignored runtime | `.runtime/` in `.gitignore` | Met |
| Privacy-safe logs | Log job_id, rule counts, filenames — not finding details | Review needed |
| Path traversal prevention | Sanitize names; zip-slip guards | **Done** — `upload_handling.py` |
| ZIP extraction safety | Limits + allowlist | Not implemented |
| SSRF protection (URL fetch) | `web_url_fetch.py` blocks private IPs | Met — keep opt-in/advanced |
| Upload size cap | `MAX_UPLOAD_BYTES` | Met |
| No private text in UI defaults | Truncated JSON details; no body quotes | Partial — improve templates |
| File deletion policy | Delete on failure + scheduled TTL | **Done** — `cleanup_expired_jobs()` |
| Bind to localhost by default for demos | `127.0.0.1` in docs | Document in ops guide |

---

## 10. Phased roadmap

| Phase | Scope | Deliverable |
|---|---|---|
| **0** | Backend contract audit | **Done** — `run_pdf_audit_full()` / `collect_pdf_layout_findings()` shared by CLI and web; parity tests in `tests/test_audit_runner.py` |
| **1** | Minimal polished UI | **Done** — enhanced Jinja templates: status banner, summary cards, triage-first layout, findings filters, privacy note |
| **2** | Upload correctness | **Done** — PDF/TeX/ZIP web upload via `upload_handling.py` and `run_audit_for_uploaded_file()` |
| **3** | Report rendering tests | **Partially done** — `report_view.py` + `polished_comments.py` + polished Jinja results page; client-side filter tests added |
| **4** | PDF page preview | Page thumbnails with finding markers (privacy-safe) |
| **5** | Polished comment coverage | All high-volume rules; remediation from `rule_loader` |
| **6** | Optional annotated PDF export | Highlight regions (no text injection) |
| **7** | Packaging / docs / demo | `pip` extra `[web]`; updated `docs/web_gui_mvp.md`; demo script |

---

## 11. Implementation-ready next tasks

1. ~~**Unify PDF audit entrypoint**~~ — **Done** — `run_pdf_audit_full()` in `audit_runner.py`; CLI and web call `collect_pdf_layout_findings` / `run_pdf_audit_full`
2. **Create `src/njit_auditor/gui/` package** (or `web/` submodule) for view models separate from routes
3. ~~**Add `run_audit_for_uploaded_file()`**~~ — **Done** — dispatches PDF / TeX / ZIP with JSON/Markdown export parity for source audits
4. ~~**Define report-view DTOs**~~ — **Done** — `ReportView`, `FindingView`, `TriagePanelView`, `SummaryCard` in `report_view.py`; `polished_comments.py` for GUI comments
5. ~~**Add `safe_extract_zip()`**~~ — **Done** — `upload_handling.py`
6. ~~**Add `detect_main_tex()`**~~ — **Done** — `upload_handling.py`
7. **Add `polished_comments.py`** — template map keyed by `(rule_id, issue_type)`
8. ~~**Enhance `web_app.py` templates**~~ — **Done** — status banner, summary cards, triage-first layout, client-side filters, upload-page polish
9. ~~**Add TeX JSON/Markdown output**~~ — **Done** — `build_source_report()` / `build_audit_report()` in `report_outputs.py`; source polished comments; report-view file/line support
10. **Tests** — upload matrix, zip-slip, schema parity, polished-comment privacy, runner/CLI parity
11. **Job TTL cleanup** — background sweeper or startup hook for stale `.runtime/web_audits/*`
12. **Docs** — update `docs/web_gui_mvp.md` after UI refresh; cross-link from README

### Known caveats before implementation

- ~~**Web audit is behind CLI**~~ — resolved; web PDF uploads use full P011–P061 via `run_pdf_audit_full`
- ~~**TeX has no JSON export today**~~ — resolved; web UI accepts PDF/TeX/ZIP (ZIP audits source, not compiled PDF)
- **URL fetch is not offline** — treat as advanced feature; offline-first messaging on landing page
- **Built-in samples expose private evaluation PDFs** — disable on public deployments
- **High-volume rules (P013/P026) remain noisy** — triage-first UX is essential for usability

---

## Related documentation

- Operations (existing MVP): `docs/web_gui_mvp.md`
- Full aggregate evaluation reference: `docs/evaluation/current_auditor_after_p061_evaluation.md`
- Project status: `docs/status/current_project_state_and_next_steps.md`
