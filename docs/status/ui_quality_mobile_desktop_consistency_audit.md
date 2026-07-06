# UI Quality, Usability, and Mobile/Desktop Consistency Audit

> **Date:** 2026-07-05  
> **Baseline:** `origin/main` @ `c9ae73eddb0183ee734a4c0a1b47c1f6424985dd`  
> **Audit target:** scratch uvicorn on `127.0.0.1:8010` with `PYTHONPATH=src` (live deployment on `:8000` **untouched**)  
> **Method:** Playwright multi-viewport checks + existing pytest mobile/desktop parity suite

## Executive summary

The current PDF-only web UI is **coherent, professional, and largely consistent across desktop and mobile**. Report pages render the **same finding counts, summary totals, topic rows, filters, download links, and advanced-section availability** at 1400px, 768px, 390px, and 360px widths. Main student flow (Summary → Recommended review order → Findings by topic → Findings in page order → Downloads → Advanced) is clear; legacy grouped/individual toggle and main Severity column/filter remain absent.

**One mechanical mobile defect** was found on `/help`: the glossary table forced horizontal page overflow at phone widths. **Two minor wording mismatches** were found between Help and the report page section title (“Review order” vs “Recommended review order”; “detected candidate inventory” in Help). This audit PR fixes the overflow and aligns Help wording.

Advanced collapsed sections still use **“candidate”** language for page-number inventory (`Detected page-number candidates`). That is intentional technical vocabulary below Downloads and is **deferred** for Esther/policy review rather than renamed in this pass.

## Samples tested

| Sample | Role | Findings | Notes |
|---|---|---:|---|
| `ester_sample_a` | General / page-number / margin mix | 39 | Primary smoke sample |
| `ester_sample_b` | High finding volume | 70 | Parity + filter usability |
| `ester_sample_d` | Very high volume + long filename | 246 | Stress test; status banner wraps safely |
| `clean_minimal.pdf` | Few findings | 2 | Synthetic fixture via upload |

## Viewports tested

| Label | Size | Used for |
|---|---|---|
| Desktop | 1400×900 | Layout density, parity baseline |
| Tablet | 768×1024 | Intermediate wrapping |
| Phone | 390×844 | Primary mobile target |
| Phone narrow | 360×780 | Narrow-device regression |

## Desktop/mobile parity

For every sample above, these matched **exactly** across all four viewports:

| Metric | Parity |
|---|---|
| Summary card values (Items to review, Pages affected, Rules flagged) | ✅ |
| Findings in page order card count | ✅ |
| Recommended review order item count | ✅ |
| Findings by topic rows and counts | ✅ |
| Default sort (`Page order`) | ✅ |
| Filter controls present (Rule, Category, Page, Confidence chips, Reset) | ✅ |
| Download links (View PDF, JSON, Markdown, Audit another) | ✅ |
| Advanced sections availability | ✅ |
| Jump-link set (modulo short “Review order” chip label) | ✅ |
| Horizontal page overflow | ✅ on report pages |

Functional checks on `ester_sample_a` (desktop):

| Control | Result |
|---|---|
| Rule filter | ✅ updates “Showing N of M findings” |
| Reset filters | ✅ restores full count |
| Sort → High confidence first | ✅ reorders cards (high-confidence P011 first) |

## Mobile usability

### Report pages (all samples)

| Check | Result |
|---|---|
| Horizontal overflow at 390px | ✅ None |
| Horizontal overflow at 360px | ✅ None |
| Finding cards readable | ✅ Issue summary, page/location, confidence badge, action button visible |
| Review note collapsible | ✅ `<details>` works |
| Filter bar | ✅ Wraps; chips and selects usable |
| Long filename in status banner | ✅ Wraps (`ester_sample_d`) |
| Download buttons | ✅ Fit via flex-wrap |
| Advanced sections | ✅ Collapse/expand cleanly |

### Help page (before fix)

| Check | Result |
|---|---|
| Horizontal overflow at 390px | ❌ Glossary table (`scrollWidth` 447 vs viewport 390) |
| Readability | ⚠️ Forced sideways scroll on phone |

### Help page (after fix in this PR)

| Check | Result |
|---|---|
| Glossary wrapped in `.table-scroll` | ✅ Contained horizontal scroll |
| Term column nowrap only ≥641px | ✅ Wraps on phone |

**Note:** An automated “clipped button” counter flagged filter chips inside horizontally scrollable `.table-scroll` regions on phone. Those elements did **not** produce page-level overflow and are treated as false positives.

## Desktop quality

| Check | Result |
|---|---|
| Section hierarchy | ✅ Clear primary vs Advanced |
| Card alignment | ✅ Consistent compact finding cards |
| Confidence badges | ✅ Present but not dominant vs issue text |
| Important actions | ✅ Page/highlight links easy to find |
| Advanced sections | ✅ Below Downloads, collapsed, labeled “Advanced:” |
| Legacy table-layout artifacts | ✅ None in main student list |

## Wording / stale terminology

### Absent from main student-facing report flow ✅

- “Grouped problems” / “All individual findings” toggle
- “Most common issues”
- Main `Severity` column/filter on report page
- `heuristic`, `bbox`, `grouped_summary`, implementation module paths

### Present by design (Advanced / reference) — deferred

| Location | Term | Recommendation |
|---|---|---|
| Report advanced section | `Detected page-number candidates` | **Defer** — Esther/policy on student-facing vs reviewer-only inventory naming |
| Report section notes / privacy note | “inventory candidates” | **Defer** — explains non-problem inventory; keep or simplify with Esther |
| `/rules` page | Severity filter | **OK** — rule reference, not audit results |

### Fixed in this PR ✅

| Location | Issue | Fix |
|---|---|---|
| `/help` results list | “Review order” vs report H2 “Recommended review order” | Align Help to **Recommended review order** |
| `/help` advanced blurb | “detected candidate inventory” | **detected page-number inventory** |
| `/help` glossary | Unwrapped wide table on mobile | `.table-scroll` wrapper + responsive term column |

### Minor polish (documented, not changed)

| Item | Notes |
|---|---|
| Jump chip says “Review order”; H2 says “Recommended review order” | Short nav label is acceptable; optional aria-label later |
| Help glossary row “Individual finding (Raw finding)” | Slightly technical; low priority rename |
| `web_ui_demo_guide.md` still says “Review order” in places | Update in a docs-only follow-up |

## Accessibility observations

| Area | Observation |
|---|---|
| Buttons / links | Action buttons and rule links have visible text |
| Headings | Logical `h1`/`h2` hierarchy on report and help |
| Confidence | Text labels (“High/Medium/Low confidence”), not color-only |
| Collapsibles | Native `<details>` / `<summary>` for Review note and Advanced |
| Focus | Filter chips use `aria-pressed` |
| Contrast | Default theme readable; no obvious low-contrast failures in audit |
| Tap targets | Filter chips and card action buttons meet reasonable mobile size |

## Screenshots

Safe UI chrome captures (no dissertation body text):

- `docs/status/ui_audit_screenshots/ester_sample_a_desktop_1400.png`
- `docs/status/ui_audit_screenshots/ester_sample_a_phone_390.png`
- `docs/status/ui_audit_screenshots/ester_sample_d_phone_390.png`

## Prioritized fixes

| Priority | Item | Action |
|---|---|---|
| **Fix now** | Help glossary mobile overflow | ✅ `.table-scroll` + responsive glossary CSS |
| **Fix now** | Help “Review order” / “candidate inventory” wording | ✅ aligned in this PR |
| **Minor polish** | Jump chip vs H2 naming | Defer optional aria-label |
| **Minor polish** | Filter bar column layout on very small phones | Defer; wraps acceptably today |
| **Defer** | Rename advanced “page-number candidates” section | Needs Esther/policy |
| **Defer** | Soften “inventory candidates” in summary notes | Needs Esther/policy |
| **Already aligned** | Report flow, compact cards, no legacy toggle | No change |

## Validation run for this audit pass

```text
ruff check .
mypy src
python -m pytest
```

Baseline before this PR: **2601 passed**.
