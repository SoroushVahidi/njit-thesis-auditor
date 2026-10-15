# Ester's October 15 student card feedback

This change updates the web result and problem-detail cards. It leaves detector output, rule IDs, JSON/Markdown reports, and historical reviewer judgments intact.

| Request | Implementation |
|---|---|
| Replace `R011` and other primary card codes | R011 is **MARGINS**; other cards use their existing category names. Rule links still target the same reference; IDs remain in collapsed technical details. |
| Remove repetition | The visible card has one page label, a location when it adds information, a short issue statement, the existing suggested fix, and one PDF action. The original comment and technical ID remain in collapsed details. |
| Make numbering meaningful | Main cards show `Issue N of M` in the displayed order. Filtering renumbers visible cards and uses the visible total. Detail pages number within their selected set. Stable original finding numbers and anchors remain available in technical details. |
| Shorten margin descriptions | R011 states the side and measured overflow when `worst_overflow_pt` is present and valid. It falls back to the existing issue label when measurement is unavailable. |
| Ask margin questions accurately | The required inch values come from the detector's existing margin constants. A detected crossing yields **No** for the page-level containment question. Margin settings remain **Needs review** because a PDF crossing cannot prove the application's configured margin values. No warning card claims **Yes** from missing evidence. Landscape pages use the binding edge. |
| Use color consistently | Links and actions are blue; finding edges and issue text are red; confidence is neutral with explicit High/Medium/Low text. Answer states use text plus color, and no positive compliance color appears without established positive evidence. |

The July feedback source of truth already called for student questions about all text within margins, and the existing P011 code already records the measured overflow and landscape binding edge. The UI uses those fields; it does not change how findings are detected.

## Synthetic before and after

These screenshots use only `tests/fixtures/web_demo/issues_pdf.pdf`. They show the first finding card from the current `origin/main` baseline and this branch at 1400 px and 390 px. The baseline repeats “Page 1” in the label, location, and action; the updated card shows it once and names the measured left-margin problem.

| Width | Before | After |
|---|---|---|
| Desktop | [Before desktop](ester_student_cards_screenshots/before_desktop.png) | [After desktop](ester_student_cards_screenshots/after_desktop.png) |
| Phone | [Before phone](ester_student_cards_screenshots/before_phone.png) | [After phone](ester_student_cards_screenshots/after_phone.png) |

The Playwright browser regression runs at both widths and found no horizontal page overflow. Page filtering showed one visible card labeled `Issue 1 of 1`; resetting restored both cards, and confidence sorting kept the real two-card total. It also checks keyboard focus on the PDF action. The PDF links and report downloads remain covered by automated tests.
