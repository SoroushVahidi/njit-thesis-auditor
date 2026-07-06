# Confidence Calibration Audit (2026-07-06)

> **Canonical confidence audit.** Pair with
> [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md) and
> [open_pr_triage.md](open_pr_triage.md).

**Baseline inspected:** `main` @ `2835510b3d330f6a8156d56ce72eb0a29f825ca1` (PR #477).  
**Branch:** `docs/confidence-calibration-audit`  
**Live deployment:** serving `2835510` — **untouched in this pass**.

---

## Executive summary

Confidence is stored canonically in `AuditFinding.details["confidence"]` (`high` / `medium` / `low`) by 30 of 65 emitted rule IDs. The presentation layer (`report_view.py`, `job.html`) collapses missing and mixed multi-level groups to a **Low confidence** public badge (three values only: High, Medium, Low).

A **mechanical UI bug** was confirmed and fixed in this pass: findings with no canonical confidence displayed **Low confidence** but had `data-confidence=""`, so the **Low filter chip hid them**. The fix normalizes empty DOM filter metadata to `low` in `job.html` without changing detector output, JSON export, or stored `details`.

Broader recalibration (P014 `centering_confidence`, P026 always-medium volume, P011 thresholds, grouped-card filtering, fourth “Needs review” bucket) is **deferred**. Retained branch `fix/confidence-grouping-sorting` was assessed as a **superseded experiment** — useful filter-bucket ideas only; do not merge wholesale.

---

## Confidence data-flow summary

```
Detector → details["confidence"] (optional)
    → audit_findings_to_json_dict() (raw preserved in findings[].details)
    → build_grouped_findings() (aggregates confidence_levels; excludes confidence from grouping key)
    → build_report_view() (FindingView: confidence_level, confidence_label, confidence_css_class)
    → web_app serializes → job.findings + job.report_view
    → job.html badges, sort (?sort=), client-side confidence filter chips
```

| Layer | Missing confidence behavior |
|-------|----------------------------|
| Storage | `details.confidence` absent or invalid |
| JSON export | Unchanged (no top-level confidence field) |
| View model | `confidence=""`, `confidence_level=""`, badge **Low** |
| DOM (after fix) | `data-confidence="low"` for filter alignment |
| Sort | Still last among confidence sorts (`_UNKNOWN_CONFIDENCE_RANK`) |

**Parallel fields (not mapped to UI):** `centering_confidence` (P014), `sequence_confidence` (P019 gaps), `match_confidence` (heading gate internals).

---

## Confidence distribution across Ester samples

Audits via `run_pdf_audit_full()` on built-in samples at `2835510`.

| Sample | Warnings | high | medium | low | missing `confidence` | % missing |
|--------|--------:|-----:|-------:|----:|-------------------:|----------:|
| A | 211 | 14 | 112 | 3 | 82 | 39% |
| B | 233 | 26 | 130 | 8 | 69 | 30% |
| C | 168 | 26 | 130 | 8 | 4 | 2% |
| D | 483 | 83 | 323 | 11 | 66 | 14% |

**Missing-confidence drivers:** P012 (annotations), P036 (TOC spacing), P035 (figure/table layout), P013 document overview, P044/P016/P051/P053/P054.

**Focus rules on sample D (highest volume):** P011 53h/13m/4l; P026 115× all medium; P035 4× missing; P037 3× medium; P068 1× low; P014/P064/P023 not fired.

**Highlight anomalies:** High confidence without highlight (P030 continued-heading on D); low confidence with tight bbox (P011, P017 on D).

---

## Rule-by-rule confidence matrix (summary)

| Category | Rule IDs | Notes |
|----------|----------|-------|
| **Sets `details.confidence`** | 30 rules (P011, P015–P026, P028–P029, P031–P034, P037–P038, P051–P052, P066–P068, P074, P078, …) | Canonical high/medium/low |
| **No `details.confidence`** | 35 rules (P001–P007, P012, **P014**, P016, **P035**, **P036**, P039–P050, P053–P062, P065) | UI collapses to Low badge |
| **Alternate field only** | P014 | `centering_confidence`: high/borderline |
| **Fixed medium** | P023, P026, P037 (roman anchors) | No gradation by evidence strength |
| **Derived** | P011 | `_group_confidence(worst_overflow_pt, count)` |
| **Per-issue-type** | P019 | medium/low; `sequence_confidence` duplicates on gaps |
| **Count-based** | P064, P068 | medium/low from entry or label counts |

### Priority rules (detail)

| Rule | Confidence source | Values | Highlight/location | Concern |
|------|-------------------|--------|------------------|---------|
| P011 | `_group_confidence` | h/m/l by overflow & count | Strong multi-bbox | Low tier can still have precise geometry |
| P014 | None (`centering_confidence` only) | UI → Low | Good heading bbox | No canonical confidence |
| P019/P037 | Hard-coded / medium | m/l; P037 always medium | Mixed bbox | `triage_tier` ≠ `confidence`; P019 prose in detailed_explanation |
| P023 | Fixed medium | medium | Body union bbox | No spread by gap ratio |
| P026 | Fixed medium | medium | First-span bbox only | 115× medium on sample D |
| P035 | None | UI → Low | Good geometry bboxes | No confidence despite deterministic checks |
| P064 | entry_count ≥ 8 | medium/low | Section-level only | Did not fire on Ester samples |
| P068 | role/signature counts | h/m/l | No bbox | Structural only |

---

## UI / filter / sort observations

| Feature | Behavior |
|---------|----------|
| **Badges** | Three public values; missing/mixed → Low display |
| **Sort** | `confidence_desc` / `confidence_asc`; mixed cards rank by highest/lowest present level |
| **Filter chips** | Apply to `.finding-row` only; **not** grouped summary cards |
| **Recommended review order** | Confidence-agnostic (FAIL → category counts → WARN) — intentional, unchanged |
| **`data-confidence-levels`** | On grouped cards; not read by current filter JS |

### Safe fix applied (this PR)

**File:** `src/njit_auditor/templates/job.html`  
**Change:** `data-confidence="{{ f.confidence_level or f.confidence or 'low' }}"` on individual finding rows and grouped occurrence rows.  
**Rationale:** Smallest change; preserves view model, JSON, sort rank for missing confidence; aligns DOM with Low badge for filter JS.

---

## Best-calibrated rules (relative)

- **P011** — confidence tracks overflow magnitude and line count; strong bbox evidence.
- **P019** — per-issue-type tiers; sequence gaps medium with neighbor context.
- **P068** — confidence scales with structural label counts.
- **P064** — confidence scales with reference entry count (when it fires).

## Likely overconfident or low-discrimination

- **P026** — always `medium` despite 115 findings on sample D.
- **P023, P037** — fixed medium regardless of measured deviation.
- **P013 page candidates** — mostly medium; long numeric IDs filtered but volume remains high.

## Likely underconfident or missing-confidence

- **P012, P036, P035** — no `details.confidence`; high volume on samples.
- **P014** — `centering_confidence` not promoted to canonical field.
- **35 rules** without confidence field — all display Low.

## Context-dependent rules

- **P011** — low overflow vs high overflow on same issue type.
- **P019** — per-page vs document-wide mixed style (medium vs low).
- **P020/P024/P017** — capitalization/caption rules with high/medium mix on sample D.

---

## Retained branch assessment: `fix/confidence-grouping-sorting`

- **16 commits** ahead of older base; tip `26fae09`.
- Adds `confidence_presentation.py` with **four buckets** (`needs_review`), mixed-orange CSS, grouped-card filtering.
- **Conflicts** with current 3-value UI policy and extensive `web_app.py` / test rewrites.
- **Do not merge wholesale.**
- **Useful ideas for later:** internal `needs_review` filter bucket, `grouped_problem_matches_filter()`, centralized normalization module.

---

## Deferred policy / design questions

1. Broad confidence recalibration across 35 missing-confidence rules.
2. P014 `centering_confidence` → `details.confidence` migration.
3. P019 `sequence_confidence` consolidation.
4. Mixed-confidence badge vs sort semantics (display Low, sort by extreme).
5. Grouped-card filtering via `data-confidence-levels`.
6. Recommended review order confidence weighting.
7. P026 always-medium on high-volume font-family sweeps.
8. P011 `_group_confidence` threshold review.
9. P064 location/highlight quality.
10. Fourth public “Needs review” bucket (rejected for this PR).

---

## Prioritized follow-up slices

| Priority | Slice | Scope |
|----------|-------|-------|
| P1 | Add `details.confidence` to P012, P036, P035 | High-volume missing-confidence rules |
| P1 | P014 canonical confidence from `centering_confidence` | Single-rule migration |
| P2 | P026 confidence gradation | Policy + detector labels only |
| P2 | Grouped-card filter or remove `data-confidence-levels` | UI/JS |
| P3 | Port `needs_review` as internal filter bucket (not public badge) | From retained branch |
| P3 | P011 threshold calibration with Esther samples | Policy input |

---

## Tests (this pass)

- `test_missing_confidence_finding_data_confidence_matches_low_filter` (new)
- `test_results_page_grouped_cards_include_mixed_confidence_filter_metadata` (comment corrected)
- `test_finding_with_missing_confidence_shows_low_confidence_badge` (clarified `confidence_level` stays empty in view model)
