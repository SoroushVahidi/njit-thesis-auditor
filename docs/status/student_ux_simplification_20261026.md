# Student workflow simplification and URL errors

Students should see what needs review, where it appears, and a short suggested
correction. Background and technical detail remain available on demand.

## Baseline and scope

The implementation stacks on `research/student-beta-validation-20261017`,
`8b13dc6c225780e9487f6a7c8e153d7b9cca6fc1` (draft #627). It reuses the
student-beta cards, synthetic public sample gate, report improvements, and PDF
error handling. The independent review found that exception-log privacy
hardening is absent from this stack and remains a separate deployment gate. The rehearsed candidate has identical templates and card
code, but also incorporates separate detector/anonymizer work. It is preserved.

Main and production were independently verified as
`4efd780dde53eea907a714df8bfed86e923ef86a`; the rehearsed candidate remained
`04f4e87f131d56b5a32926c8c0db34295d228cd2`. The open draft stack #625–#633
was inspected; this change does not modify those branches or PRs.

The design follows `ester_feedback_source_of_truth.md`,
`ester_student_cards_20261015.md`, and October 25 QA issues I06–I13:
shorter primary copy, wider tablet corrections, optional background, readable
filter labels, dynamic status semantics, and spaced mobile actions. October 26
same-host URL diagnostics established a Cloudflare challenge, not a FastAPI 403.

No detector, severity, threshold, guideline, geometry, report-generation,
scheduling, access-control, retention, or anonymizer implementation changes.
The only validation addition rejects malformed URL ports before network access.

## Presentation

- Upload is the primary action; URL import and synthetic examples are optional.
- A visible upload notice says processing occurs on this server, storage is
  temporary, and valid result links provide access. It links directly to About.
- About covers use, findings, limits, privacy, actual configured retention,
  FAQs, and version. Existing Help and Rule Reference destinations remain.
- Findings precede optional coverage/review guidance. One collapsed
  "Why is this flagged?" disclosure retains full corrections, explanations,
  margin questions, and nested technical details.
- Correction text is web-only. Unknown text and conditional instructions are
  retained; there is no new sentence or character truncation. Lower-confidence
  unqualified actions receive review wording. Structured findings and report
  correction text remain unchanged. The separate `student_web_action` field
  prevents web edits from affecting the report renderer's existing action field.
- Filters use names instead of visible internal rule IDs. Native controls,
  disclosure keyboard behavior, focus indicators, skip navigation, live counts,
  and processing status semantics remain available.

The correction review covered all 61 suggested-fix expression sites in the
application/rules, 86 rule-default remediations (including non-web checks),
58 issue overrides (29 nonempty), and seven TOC actions. Eleven exact wording
pairs were shortened, plus conservative caption/reference cleanup. Existing
short actions were reused. Conditional font-family guidance is deliberately
longer: removing its accepted-font and permitted-exception clauses would lose
important information. The original advice remains in optional details and
exports for every rewritten correction.

Examples:

| Before | Primary text after |
|---|---|
| Remove the number or label in front of each publication/presentation entry; keep the References citation format without numbering. | Remove each publication or presentation entry's number, keeping the References citation format. |
| Single-space the wrapped lines within this heading; keep normal spacing between heading and body. | Check whether to single-space this heading's wrapped lines, keeping normal spacing before the body. (Medium confidence.) |
| HTTP error 403: Forbidden | The source website blocked the request. Download the PDF yourself and upload it here. |

The URL error title is "Couldn't download the PDF." A security check is named
only for a 403 with `cf-mitigated: challenge`; generic 403, 404, 5xx, timeout,
connection failure, invalid links, HTML, and size failures have short actions.
No availability promises, identity changes, cookies, challenge solving, or
access-control workarounds are introduced.

## Reproducible measurement

The 11 reviewed wording pairs contain **234 words before and 138 after: 41.0%
less**. Count words with `re.findall(r"\b[\w’'-]+\b", text)` over keys/values
of `student_actions._SHORT_ACTIONS`. Dynamic uncertainty prefixes are additional
words and are excluded from this paired-copy measure.

Run the actual-browser comparison from this branch:

```sh
python scripts/student_ux_review.py \
  --baseline /path/to/unchanged/student-beta-worktree \
  --output /path/to/review-artifacts \
  --axe-script /path/to/local/axe.min.js
```

Use the same Python/dependency environment for both sources. The script uploads
only the committed synthetic `issues_pdf.pdf` to owned loopback servers, waits
for findings, saves screenshots, and compares JSON content after excluding the
per-job ID and generation timestamp. It stops its own servers.

`VISIBLE_EXPLANATION` in the script counts each rendered text node once inside
paragraphs, section notes, privacy notes, informational notices, and review
steps. It excludes controls, headings, findings, code, navigation/footer, and
closed disclosures. The main element (or legacy body) defines the scope.
Each sample is saved as text so the count can be independently checked.

At all four widths, homepage explanations were **306 → 51 words (83.3% less)**;
results explanations were **572 → 127 (77.8% less)**. These exceed the approximate
30–50% target because background moved to About/optional disclosures, rather
than requirements being arbitrarily abbreviated. They measure initial reading
load, not total information available throughout the site. Findings, correction
pairs, About content, optional disclosures, and exports are separate measures.

## Validation and limits

- Full public/synthetic snapshot: **4,768 passed, 46 deselected**, no failures or
  skips, in 109 seconds. Private-document directories were omitted before
  materialising the snapshot. Reviewed private-fixture cases and one real
  guideline-PDF case were excluded; no confidential document was processed.
- Ruff and mypy pass. Relevant existing tests now assert the revised labels,
  optional details, and relocated privacy content. Historical sample IDs in one
  route test were replaced with the existing synthetic sample.
- Chromium 148: end-to-end workflow at 320, 390, 768, and 1440 CSS px, including
  real synthetic upload, mocked valid URL, 403/404/timeout/invalid-PDF messaging,
  filter/renumber/sort behavior, keyboard navigation/disclosures, highlighted
  PDF retrieval, and all report exports.
- Before/after rendered review: no horizontal overflow or JavaScript errors;
  unchanged exported finding content after run-metadata exclusion.
- axe-core 4.10.3: zero violations on homepage, results, and About at all four
  widths. This is not a screen-reader user study or all-browser certification.
- Representative synthetic publication/heading/font cards were separately
  rendered before/after. Long conditional font advice remains intact.

A fresh unconstrained install initially selected PyMuPDF 2.0 and changed an
existing geometry-test expectation. Validation was repeated using the
rehearsed environment's dependencies (including PyMuPDF 1.28.2, FastAPI 0.136.3,
Playwright 1.60.0). The untouched baseline and implementation pass the geometry
check in that environment. Dependency manifests were not changed in this UI PR.

No live repository availability is required by tests. No production URL audit,
historical sample audit, remote Actions run, merge, restart, or deployment was
performed. Screenshots, logs, constraints, and exact full-suite commands are
local review artifacts under `/tmp/njit-student-ux-20261026/`, not committed
student documents or generated report outputs. External repository access and
formal stakeholder acceptance remain separate questions.


## October 26 integration corrections

The follow-up to the independent review adds eight subtype-specific primary
corrections, qualifies the opening instruction, and retains complete source
correction text in optional explanations and exports. Older incomplete source
text is labelled an excerpt. Restoring complete catalog guidance also removes
internal routing references and authoring notes from its student-facing wording.
Raw detector findings, severity, measurements, and locations remain unchanged;
grouped JSON correction strings intentionally become complete where truncated.

Report attribution now distinguishes Biographical Sketch publications from body
paragraph spacing. Numbering comes from the documented October 6 reviewer
instruction; citation-style consistency is the GSO sheet topic. Annotation
advice is identified as project guidance with no specific GSO sheet item
established. No requirement numbers are invented. The 83-row matrix remains
45 partial, 32 manual, 5 unimplemented, and 1 unresolved conflict, including the
List of Figures capitalization conflict.

The earlier validation and unchanged-manifest statements above describe the
original snapshot. The correction follow-up declares Playwright in the dev
extra, changes the image fixture's proportions explicitly, and qualifies a
PyMuPDF minimum using measured compatibility results. See the
[test setup and compatibility policy](../implementation/student_ux_test_setup.md).

Inherited deployment gates remain open and outside this correction task:
IPv4-mapped IPv6 destination validation, PDF-failure logging, and an enforced
per-audit deadline. No changes to those implementations, production, services,
anonymizer behavior, or URL security restrictions are made here. Merge review
is separate from deployment and November student-pilot authorization.
