# Restoring the issue-type summary table

## What was reported

Soroush reported that the results page used to show a table/summary listing
the number of problems by type, and that he was no longer seeing it.

## Was it removed intentionally, or lost as a side effect?

Neither, exactly — it was **never deleted**, but it was **effectively hidden
as an unrequested side effect** of an otherwise-correct Ester-alignment change.

History, from `git log -- src/njit_auditor/templates/job.html` and the
corresponding merged PRs:

1. **#441** ("Declutter student-facing report summary into root-cause
   cards") merged the original standalone "Summary by problem type" table
   into a set of richer per-category cards.
2. **#448** ("restore findings-by-topic table") brought back a dedicated,
   always-visible **"Findings by topic"** section — one row per category,
   sorted by count, with a "Review all" link. This is the count-by-type
   table.
3. **#450** trimmed it to a compact 3-column shape (`Topic`, `Findings`,
   `Review all`) for mobile.
4. **#451** removed the separate, more verbose "Most common issues" cards
   section as redundant with "Findings by topic" — the count table itself
   was untouched and stayed visible.
5. **#479** ("Align student-facing warnings with Ester Column C/E and
   page-order-first UI") moved "Findings by topic" to *after* "Findings in
   page order", per Ester's explicit request that page-order findings come
   first. That reordering was correct and is preserved. However, in the same
   commit the section was **also wrapped in a collapsed `<details>`
   disclosure** and its heading was downgraded to "secondary category
   index." Nothing in Ester's feedback asked for the table to be collapsed
   or demoted — that was bundled into the reorder as an implementation
   choice.

Because HTML `<details>` content is still present in the raw response body
whether open or collapsed, every existing test that checked for the string
"Findings by topic" or the `category_summary` rows kept passing after #479 —
the table was still *in the page*, just closed by default and easy to miss
on load. That's why it disappeared from view without any test catching it
and without any commit describing it as a removal.

## Why restoring a compact, visible version is compatible with Ester's feedback

Ester's actual asks (per the product interpretation for this task) were:

- Findings in page order before Findings by Topic.
- A simpler interface.
- Information appearing just once.
- Student-facing language aligned with her Column C/E wording.

Un-collapsing "Findings by topic" does not conflict with any of these:

- **Page order first** — unchanged. The section stays exactly where #479 put
  it, after `#section-findings`. `test_report_section_order_page_before_topic`
  and `test_nav_jump_links_page_order_before_topic` still pass.
- **Simpler interface / information once** — the table remains the compact
  3-column shape from #450 (`Topic`, `Findings`, `Review all`). It shows only
  a count and a link per category; it does not repeat the polished
  explanation text or full finding details shown in "Findings in page
  order," so there is no duplication of content, only a duplication of
  *categorization* (which is the table's entire purpose — a count summary by
  design restates counts, not explanations).
- **Student-facing language** — rows use `humanize_cat` category labels
  ("Margins / overflow", "Spacing / blank lines", etc.), not internal `P0##`
  rule IDs or "Problem N" labels.

## What was restored

`src/njit_auditor/templates/job.html`:

- `#section-topics` ("Findings by topic") is a plain, always-visible
  `<section>` with an `<h2>` heading again, instead of a collapsed
  `<details>`/`<summary>` disclosure. Position (after "Findings in page
  order," before "Downloads") and the compact 3-column table shape are
  unchanged.
- The "Recommended review order" bullet for "Findings by topic" no longer
  calls it a "secondary index" — reworded to describe a visible summary
  table, matching the restored presentation.

No backend, JSON/Markdown export, detector, rule ID, category-key, or
sorting changes. `category_summary` in `web_app.py::_job_page_context` is
unchanged.

## What remains deferred

- The richer per-rule "Most common issues" triage panels removed in #451
  are not restored — Ester's feedback favors the simpler compact table, and
  `report_view.triage_panels` still backs the Markdown/JSON export's own
  "Most common issues" section, so that data is not lost, just not
  re-added to the web page.
- No wording changes were made to the table's row content (category labels,
  counts, "Review all" action) beyond the section heading/description — those
  already matched Ester's simplification and labeling requirements.
