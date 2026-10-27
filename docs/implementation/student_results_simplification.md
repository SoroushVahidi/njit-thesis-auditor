# Student results simplification

Results use one concise limitation disclosure and link to NJIT's official review
process page, which links the current self-assessment sheet. Coverage details
are on About, including every existing topic's automatic/manual descriptions,
the five unimplemented requirements, PDF extraction limits, and the unresolved
List of Figures case conflict. The 83-requirement classification remains 45
partially automated, 32 manual review, 5 unimplemented, and 1 unresolved conflict.
The coverage data and developer render helpers retain their existing values.

PDF, text (both student renderers), and PDF-audit Markdown exports use the same
short disclosure instead of the long coverage inventory and repeated generic
caveats. They retain document identity, finding numbers, locations, requirements,
complete existing correction text, and relevant file-specific failed-check
notices. PDF reports keep the source pages and existing highlighting/numbering.
Markdown/plain text keep readable confidence labels; portable Markdown does not
provide dependable badge colors across viewers.

A shared presentation palette colors High confidence red, Medium confidence
amber with dark text, and Low confidence blue. Website cards, drilldowns, filter
chips, and PDF labels use it. Selected filters use an outline and aria-pressed;
text labels convey levels without relying on color. Severity styling and all
confidence classification/fallback logic remain unchanged. About explains once
that confidence describes certainty rather than seriousness. Optional technical
introductions remain inside their existing disclosures.

## Verification

Use synthetic documents only. Regression tests cover absence of repeated
coverage labels, exactly one disclosure, complete coverage in About, independent
confidence/severity, text contrast, and PDF confidence colors. Browser tests
exercise Chromium and Firefox at 320, 390, 768, and 1440 pixels: actual computed
colors including selected filters, keyboard activation, optional details,
About, external-request rejection, overflow, and badge/button separation.
The existing source web/desktop workflow tests also cover exports/highlights.
No manual screen-reader validation or native Windows qualification is claimed.

Palette foreground/background contrast is 6.54:1 (high), 7.79:1 (medium), and
6.59:1 (low), exceeding WCAG AA's 4.5:1 normal-text threshold. Badge boundaries
also exceed 3:1 against their backgrounds. This does not assert complete WCAG
conformance of the application.

Before/after evidence uses the same three-finding synthetic presentation fixture
and four actual synthetic PDF audits at the parent revision and this branch.
Normalized JSON, full student finding fields, highlighted-page drawings, text
finding sections, and Markdown finding sections match. Only volatile audit IDs,
paths, and timestamps are normalized; finding IDs and measurements stay exact.
The presentation fixture explicitly combines confidence levels and severities;
it is not evidence that a detector emitted those particular combinations.

Initially rendered page text counts exclude collapsed details, hidden content,
and nonselected select options. The full default results page falls from 510 to
454 words (11%); finding information is retained. Viewport-only counts rise
slightly because the requested disclosure appears near the beginning. Captures
of both viewport and full-page counts, results, each badge, About, and combined
PDF/source/report first pages are retained outside Git. Exact test results and
report word counts are recorded in the task's external validation report.

This branch is stacked on draft #635. It does not merge, deploy, publish desktop
artifacts, enable downloads, modify licensing/security, or change detectors.
