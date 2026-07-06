# Problem Drill-Down Audit

> **Historical note:** This document predates the final #9 cleanup snapshot (2026-07-05).
> Section names such as "Summary by problem type" describe the pre-cleanup layout.
> For the current report flow, see [current_project_state_and_next_steps.md](../status/current_project_state_and_next_steps.md).

**Date:** 2026-06-16  
**Baseline:** main after PR #321 (issue-type explanations)

---

## What Existed Before

### Routes

Both category and rule drill-down routes existed and worked:

| Route | Status |
|---|---|
| `/audits/{job_id}/problems/category/{category_slug}` | ✓ existed |
| `/audits/{job_id}/problems/rule/{rule_id}` | ✓ existed |
| `/audits/{job_id}/problems/rule/{rule_id}/issue-type/{issue_type_slug}` | ✗ missing |

### UI entry points

| Element | Status before |
|---|---|
| "By category" section: compact clickable chips | ✓ worked, but compact and unlabeled |
| "Summary by rule" table: rule IDs clickable | ✓ linked to rule reference `/rules#{rule_id}`, NOT drill-down |
| "Summary by rule" table: category names | ✗ plain text, not clickable |
| "Summary by rule" table: "View all" button | ✗ missing |
| Issue-type "View all findings of this type" link | ✗ missing |

---

## What Was Missing

1. **No issue-type drill-down route.** Students could not navigate to all findings of a specific issue type (e.g., all `pdf_annotation_detected` findings).
2. **Rule IDs in the summary table linked to the rule reference** (`/rules#P015`), not to the drill-down page. Students wanting to see all P015 findings had no obvious single click.
3. **Category names in the summary table were not clickable.** The category was shown as plain text; the category drill-down was only reachable from the "By category" chips.
4. **No "View all" button in the rule summary.** No explicit primary action per row.
5. **"By category" was compact chips** without explicit "View all" labels, making the navigation intent unclear.
6. **Issue-type `<details>` blocks had no drill-down link** — once a student expanded "What does this mean?" for an issue type, there was no path to see all instances of it.

---

## What Was Added

### New route

`GET /audits/{job_id}/problems/rule/{rule_id}/issue-type/{issue_type_slug}`

- Filters `job.findings` by both `rule_id` and `issue_type`.
- Reuses `_problem_group_examples` and `problem_group.html` template.
- `issue_type_slug` uses hyphens (e.g., `pdf-annotation-detected`).
- Returns 404 when no matching findings exist.
- `group_kind = "issue_type"` so the template renders the issue_type_label as the card title.

### Jinja2 filter: `issue_type_slug`

`{{ example.issue_type | issue_type_slug }}` → `pdf-annotation-detected`

Registered alongside the existing `category_slug` filter.

### "Summary by problem type" section (was "By category")

Replaced the compact chip row with a proper table:

| Problem type | Findings | |
|---|---|---|
| Page numbering | 4 | View all |
| Font formatting | 3 | View all |
| …  | … | … |

- Sorted by count descending (Python-side, via `category_summary` context var).
- Problem type name and "View all" both link to the category drill-down.
- Jump link updated from "By category" → "By problem type".

### "Summary by rule" improvements

- **Category column**: now a clickable link to the category drill-down.
- **New "View all" column**: explicit button linking to `/problems/rule/{rule_id}`.
- Rule ID still links to the rule reference (`/rules#{rule_id}`) for context.

### Issue-type "View all" link

Inside every `<details class="issue-type-help">` block (in both `job.html` grouped cards and `problem_group.html` example cards), a "View all findings of this type →" link is now shown when the details are expanded. Links to the new `/problems/rule/{rule_id}/issue-type/{slug}` route.

---

## Routes Supported After This Change

| Route | Group kind | Template |
|---|---|---|
| `/audits/{id}/problems/category/{cat_slug}` | "category" | problem_group.html |
| `/audits/{id}/problems/rule/{rule_id}` | "rule" | problem_group.html |
| `/audits/{id}/problems/rule/{rule_id}/issue-type/{issue_type_slug}` | "issue_type" | problem_group.html |

---

## Mobile/Desktop Parity

- Same `category_summary` list used on both viewports.
- Same rule summary table rows on both viewports.
- Same issue-type links in details blocks on both viewports.
- No mobile-only/desktop-only content branches added.

---

## Limitations

1. **Issue-type slugs use hyphens** (`pdf-annotation-detected`). If the raw `issue_type` contains hyphens already (none currently do), slug → issue_type round-trip would be lossy. Acceptable given current naming convention.

2. **Issue-type drill-down is rule-scoped.** The URL is `/problems/rule/{rule_id}/issue-type/{issue_type_slug}`, not a global `/problems/issue-type/{issue_type_slug}`. This is intentional: the same issue_type name could theoretically appear in different rules with different semantics.

3. **Category sort order** is determined Python-side (count descending) and locked into the template context. If counts change (re-audit), the context is rebuilt from scratch.

4. **Playwright/browser-layout parity**: only server-rendered HTML is tested. CSS stacking/wrapping on real devices is not tested.

---

## Validation

```
ruff check .    → All checks passed!
mypy src        → Success: no issues found in 93 source files
python -m pytest → 1409 + tests passed
```
