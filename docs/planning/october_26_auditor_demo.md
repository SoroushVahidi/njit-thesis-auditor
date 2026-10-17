# October 26 student auditor demonstration

**Meeting:** 26 October 2026, 3:45–4:30 PM EDT. Use only synthetic PDFs. This is a demonstration of a review aid, not evidence of GSO acceptance or a production pilot.

| Time | Demonstration | Evidence and speaking point |
|---|---|---|
| 3:45–3:50 | State purpose | Upload a thesis PDF to find likely format issues and identify items requiring student review. The official [GSO second-review sheet](https://docs.google.com/document/d/1XyWoOU8OK_DWuBQXDzE39NMAIb4caXBg/edit) remains the document students submit. |
| 3:50–3:55 | Show October 15 feedback changes | MARGINS topic, `Problem N of M`, one visible page label, short measured issue, blue links, red warnings, neutral confidence, collapsed details. The margin setting questions say “Needs review” when the PDF cannot prove a yes/no answer. |
| 3:55–4:05 | Upload synthetic multi-issue PDF | Use the committed synthetic `tests/fixtures/web_demo/issues_pdf.pdf` or an approved RUN fixture. Explain that a malformed/unsupported upload produces a readable error. |
| 4:05–4:15 | Triage findings | Filter by page/category, sort, open a highlighted page, inspect multiple findings on one page, and describe a correction in the source document. A highlight is shown only with reliable coordinates. |
| 4:15–4:22 | Download report | Open the combined PDF and appended report: document name, UTC audit date, findings, physical and printed pages when determined, GSO area, action, manual work, and incomplete-check notice. Show that “no findings” is not a passing verdict. |
| 4:22–4:27 | Coverage and limits | Review margin/font/pagination checks; show equations, committee ordering, advisor style, and sheet attestation as manual. Mention Ester’s documented LaTeX font exception and the sheet-versus-later-guidance conflict for List of Figures case without declaring new policy. |
| 4:27–4:30 | November gate and feedback | Ask whether cards and report are understandable for a second-review student, which false positives matter, and whether manual items are conspicuous. Record stakeholder decisions separately from code merge status. |

Before the meeting, repeat the synthetic route/browser run on the presentation machine and inspect the downloaded PDF at normal zoom. Keep a local synthetic backup PDF and a screenshot. The practical offline anonymizer is progressing in a separate workstream; request its independent evidence before presenting distribution readiness. PR #620 remains subject to Windows validation. Do not claim an offline Windows app or anonymizer is ready for students on the basis of this demo.
