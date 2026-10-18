# Student beta readiness — 16 October 2026

## Source, baseline, and decision boundary

The source for the matrix is the [GSO second-review self-assessment sheet](https://docs.google.com/document/d/1XyWoOU8OK_DWuBQXDzE39NMAIb4caXBg/edit), a DOCX fetched as text through the connected Google Drive tool on 16 October 2026 (file ID `1XyWoOU8OK_DWuBQXDzE39NMAIb4caXBg`). Its introductory instruction says the student submits the sheet with the second-review document. This auditor report supports that review; it cannot replace the sheet or grant GSO approval.

This isolated branch started at `4efd780dde53eea907a714df8bfed86e923ef86a` with a clean tree. PR #619 was merged; #620 remained open, and #621–#623 were drafts. Those branches were not modified. The detector thresholds, IDs, raw guidelines, and historical adjudications remain unchanged. This review uses the rendered PR #619 UI and the existing [coverage disclosure](../../src/njit_auditor/coverage_disclosure.py), [student report](../../src/njit_auditor/student_pdf_report.py), and [web app](../../src/njit_auditor/web_app.py). A catalog entry is never treated as proof that a document was checked successfully.

## Status and evidence keys

- **AUTOMATED_AND_VERIFIED**: a narrow automatic check has a meaningful regression and a supported outcome. It does not mean the entire checklist item passes on any particular upload.
- **AUTOMATED_PARTIAL**: the detector sees only some cases or a PDF makes proof impossible.
- **MANUAL_REVIEW**: no reliable automatic conclusion; the student must inspect it.
- **NOT_IMPLEMENTED**: an objective requirement could be checked but is not currently covered.
- **REQUIRES_POLICY_CLARIFICATION**: later reviewer guidance differs from the sheet or the wording cannot be reconciled confidently.

Evidence **C** means the implementation and its documented limitations in `coverage_disclosure.py`; **R** means the relevant source rule and `tests/` regression; **W** means synthetic HTTP route/report verification recorded in `RUN/TEST_RESULTS.md` outside Git; **E** means later documented reviewer guidance in `docs/status/ester_feedback_source_of_truth.md`, `docs/status/ester_feedback_round_20261005.md`, or a rule-specific status note. A rule ID in this table identifies an implementation path, not a claimed successful evaluation. In the report column, **finding** means a warning may appear; **scope** means the student report lists the category and its manual checks; **none** means no item-specific result. Manual verification is required for every row even when a finding exists. The 83 sheet requirements below classify as 45 automated partial, 32 manual review, 5 not implemented, and 1 requiring policy clarification. None warrants a whole-requirement verified-pass label.

## Complete sheet-to-auditor matrix

| GSO requirement (paraphrased) | Rule(s) | Status | Automatic checkability / reliability | Report | Manual verification | Evidence | Later Ester conflict | Action |
|---|---|---|---|---|---|---|---|---|
| Left margin 1.5 in; other margins 1 in throughout | P011 | AUTOMATED_PARTIAL | Text crossings; configured margins cannot be read from PDF | finding, scope | Check source settings and all pages | C,R,W | None | Retain conservative questions |
| Nothing except page numbers in margins | P011 | AUTOMATED_PARTIAL | Text only; image/vector overflow may be missed | finding, scope | Inspect images, rules, headers | C,R | None | Manual reminder |
| Entire-document Arial/Times New Roman 12 pt | P026 | AUTOMATED_PARTIAL | Main body majority heuristic; 11–13 pt accepted; front matter/tables exempt | finding, scope | Check font roles and actual source styles | C,R,E | Ester confirmed Computer/Latin Modern for appropriate LaTeX on 23 September | Preserve documented exception |
| Roman numerals in front matter | P013,P019,P029,P037 | AUTOMATED_PARTIAL | Detects parsed numeral sequences, can miss image numbers | finding, scope | Inspect every front-matter footer | C,R | None | Retain |
| No number on Abstract, Title, Copyright, Approval | P019,P022,P028 | AUTOMATED_PARTIAL | Depends on page classification/text extraction | finding, scope | Inspect those pages | C,R | None | Retain |
| Biographical Sketch first numbered page, iv | P019,P037 | AUTOMATED_PARTIAL | Detects common sequence and anchor | finding, scope | Check physical and printed page | C,R | None | Retain |
| Arabic numerals only in main text | P013,P019,P029 | AUTOMATED_PARTIAL | Parsed footer numbers; image numbers can be missed | finding, scope | Inspect all body pages | C,R | None | Retain |
| Start 1 at Chapter 1 and continue through references/end | P019,P037,P085 | AUTOMATED_PARTIAL | Sequence and structural cues; exact endpoints not always established | finding, scope | Compare chapter and final reference pages | C,R | None | Manual endpoint check |
| Same dissertation title on Abstract, Title, Approval | P074 | AUTOMATED_PARTIAL | Flags clear differences when two titles are readable | finding, scope | Compare spelling and spacing on all three | C,R | None | Retain |
| Title page uses program template | — | MANUAL_REVIEW | Program template not available to detector | scope | Compare with program template | C | None | Provide manual item |
| Graduation month is December, May, or August | P025 | AUTOMATED_PARTIAL | Text/metadata extraction only | finding, scope | Confirm actual graduation date | C,R | None | Retain |
| Approval names have Dr./Mr./Ms. honorific | — | MANUAL_REVIEW | Names and roles ambiguous in PDF | scope | Inspect every name | C | None | Manual item |
| Advisor appears first | P068 | AUTOMATED_PARTIAL | Advisor label may be found; order not proved | finding, scope | Check first committee entry | C,R | None | Manual item |
| Own department members before others | — | MANUAL_REVIEW | Department affiliation external to PDF | scope | Confirm departmental membership/order | C | None | Manual item |
| Own department rank order and alphabetic ties | — | MANUAL_REVIEW | Rank/person data cannot be trusted automatically | scope | Check each rank and surname | C | None | Manual item |
| Other NJIT departments follow own department | — | MANUAL_REVIEW | Affiliation and order require human context | scope | Compare affiliations | C | None | Manual item |
| External members last with institution, company, city, state | — | MANUAL_REVIEW | Role and field completeness ambiguous | scope | Verify all external entries | C | None | Manual item |
| Bio Sketch Author/Degree/Date/Major fields align | — | MANUAL_REVIEW | Field alignment is not a verified check | scope | Inspect four field baselines | C | None | Manual geometry check |
| Bio Sketch presentations/publications match reference style | P067 | AUTOMATED_PARTIAL | Numbering, spacing, chronology only; citation style match unproved | finding, scope | Compare entries with References | C,R | None | Manual comparison |
| Acknowledgments heading plural and ends in s | P038 | AUTOMATED_PARTIAL | Heading text if extractable | finding, scope | Read heading | C,R | None | Retain |
| Capitalize Advisor and Committee Members | — | MANUAL_REVIEW | Context-sensitive wording | scope | Check terms | C | None | Manual item |
| First acknowledgments paragraph thanks advisor | — | MANUAL_REVIEW | Semantic judgment | scope | Read first paragraph | C | None | Manual item |
| Second paragraph thanks committee | — | MANUAL_REVIEW | Semantic judgment | scope | Read second paragraph | C | None | Manual item |
| Third paragraph thanks technical/scientific support | — | MANUAL_REVIEW | Semantic judgment | scope | Read third paragraph, if applicable | C | None | Manual item |
| Fourth paragraph names funding/grant number | — | MANUAL_REVIEW | Funding applicability and grant validity need student | scope | Check source and grant number | C | None | Manual item |
| Fifth paragraph thanks friends/peers/colleagues if applicable | — | MANUAL_REVIEW | Optional content | scope | Check if applicable | C | None | Manual item |
| Final paragraph thanks family if applicable | — | MANUAL_REVIEW | Optional content | scope | Check if applicable | C | None | Manual item |
| Full names used in acknowledgments | — | MANUAL_REVIEW | Identity cannot be established from PDF alone | scope | Check every named person | C | None | Manual item |
| TOC heading centered, bold, all caps | P038 | AUTOMATED_PARTIAL | Heading/style geometry can miss font flags | finding, scope | Inspect TOC heading | C,R | None | Retain |
| Continued TOC heading on next page, second line, single spaced | P014,P058 | AUTOMATED_PARTIAL | Continued heading detection/spacing heuristic | finding, scope | Inspect each TOC continuation | C,R | None | Retain |
| TOC chapter titles all caps | P018 | AUTOMATED_PARTIAL | Extractable entries only | finding, scope | Inspect all chapter entries | C,R | None | Retain |
| TOC level 2 in title case | P018 | AUTOMATED_PARTIAL | Case heuristic; proper nouns ambiguous | finding, scope | Read capitalization | C,R | None | Retain |
| TOC level 3 in sentence case | P018 | AUTOMATED_PARTIAL | Only clear violations flagged | finding, scope | Read ambiguous cases | C,R | None | Retain |
| TOC omits level 4/5 titles | — | MANUAL_REVIEW | Mapping headings to entries not reliable | scope | Compare TOC to body hierarchy | C | None | Manual item |
| Multiline TOC titles single spaced | P018,P036 | AUTOMATED_PARTIAL | Flags large gaps, not proof of exact single spacing | finding, scope | Inspect wraps | C,R | None | Retain conservative threshold |
| TOC page numbers right aligned and match section starts | P018,P032 | AUTOMATED_PARTIAL | Alignment/order checked; actual destination only partially | finding, scope | Follow each TOC number | C,R | None | Manual destination check |
| TOC level 2/3 indentation shows hierarchy | P039 | AUTOMATED_PARTIAL | Geometry inference | finding, scope | Check all levels | C,R | None | Retain |
| TOC leaders connect titles to page numbers | P075 | AUTOMATED_PARTIAL | Style consistency checked; weak extraction may miss | finding, scope | Inspect leaders | C,R | None | Retain |
| List of Tables titles title case | P018 | AUTOMATED_PARTIAL | Case heuristic | finding, scope | Read entries | C,R | None | Retain |
| Multiline List of Tables titles single spaced | P018,P036 | AUTOMATED_PARTIAL | Large-gap heuristic | finding, scope | Inspect wraps | C,R | None | Retain |
| List of Tables leaders connect to page numbers | P055 | AUTOMATED_PARTIAL | Pattern and alignment detection | finding, scope | Check entries and destinations | C,R | None | Retain |
| List of Figures descriptions sentence case | P018 | REQUIRES_POLICY_CLARIFICATION | Existing check follows later title-case guidance | finding, scope | Confirm current GSO expectation | C,E | Sheet says sentence case; later reviewer guidance says title case | Do not change rule until clarified |
| List of Figures descriptions use punctuation | P040 | AUTOMATED_PARTIAL | Terminal punctuation only | finding, scope | Check wording and punctuation | C,R | None | Retain |
| Figure part letters consistent in List of Figures | — | MANUAL_REVIEW | Matching parts across entries unreliable | scope | Compare part labels | C | None | Manual item |
| Body text double spaced | P016 | AUTOMATED_PARTIAL | PDF line-spacing heuristic with exclusions | finding, scope | Inspect body and exceptions | C,R | None | Retain |
| Bullet lines single spaced, bullets double spaced apart | — | NOT_IMPLEMENTED | Distinguishing nested lists and wraps needs new robust geometry | scope | Inspect lists | C | None | Pilot gap; avoid noisy rule |
| All multiline titles single spaced | P015,P023,P036 | AUTOMATED_PARTIAL | Some headings/captions/wraps only | finding, scope | Inspect every wrapped title | C,R | None | Manual reminder |
| Section first paragraph unindented, later ones indented | P015 | AUTOMATED_PARTIAL | Structure/indent heuristics | finding, scope | Inspect each section | C,R | None | Retain |
| Chapter titles bold, centered, all caps | P020,P027 | AUTOMATED_PARTIAL | Case/geometry/style extraction incomplete | finding, scope | Inspect chapter headings | C,R | None | Retain |
| Two blank lines after chapter title | P015 | AUTOMATED_PARTIAL | Spacing geometry, exact line count uncertain | finding, scope | Check visual gap | C,R | None | Retain |
| Level 2 title case, centered, bold | P020,P027 | AUTOMATED_PARTIAL | Case checks stronger than style/alignment | finding, scope | Inspect all three properties | C,R | None | Retain |
| Level 2 text starts next line | — | MANUAL_REVIEW | Run-in geometry context ambiguous | scope | Inspect text start | C | None | Manual item |
| Level 3 sentence case, aligned, bold | P020,P027 | AUTOMATED_PARTIAL | Numbered case checked; style/alignment weaker | finding, scope | Inspect all properties | C,R | None | Retain |
| Level 3 text starts next line | — | MANUAL_REVIEW | Layout context ambiguous | scope | Inspect text start | C | None | Manual item |
| Level 4 sentence case and terminal period | P020 | AUTOMATED_PARTIAL | Numbered heading text only | finding, scope | Inspect each heading | C,R | None | Retain |
| Level 4 period followed by space and tab | — | MANUAL_REVIEW | Tab lost in PDF text extraction | scope | Check source document | C | None | Manual item |
| Level 4 bold/aligned and text on same line | P027 | AUTOMATED_PARTIAL | Run-in/style inference limited | finding, scope | Inspect each heading | C,R | None | Manual reminder |
| Level 4 omitted from TOC | — | MANUAL_REVIEW | Cross-document hierarchy matching unreliable | scope | Compare body and TOC | C | None | Manual item |
| Level 5 sentence case, italic, period, not bold | P020,P027 | AUTOMATED_PARTIAL | Case/style flags incomplete | finding, scope | Inspect all properties | C,R | None | Manual reminder |
| Level 5 text next line and omitted from TOC | — | MANUAL_REVIEW | Cross-document matching unreliable | scope | Compare heading and TOC | C | None | Manual item |
| Table title above table, title case, left aligned | P017,P035 | AUTOMATED_PARTIAL | Caption geometry/case checks, tables may be image/vector | finding, scope | Inspect each table | C,R | None | Retain |
| Only Table and number bold | — | MANUAL_REVIEW | Span-level bold unreliable for all caption formats | scope | Inspect caption style | C | None | Manual item |
| Tables centered | P035 | AUTOMATED_PARTIAL | Geometry estimate on extractable tables | finding, scope | Inspect all tables | C,R | None | Retain |
| Table text may differ from 12 pt | P026 | AUTOMATED_PARTIAL | Detector excludes many table spans; exception honored | scope | Check readability | C,E | Sheet explicitly permits exception | Keep exception |
| Wrapped table-cell text single spaced | — | MANUAL_REVIEW | Cell segmentation unreliable in PDF | scope | Inspect cells | C | None | Manual item |
| Table source below table in 10 pt if present | — | MANUAL_REVIEW | Source identification and exception unreliable | scope | Inspect source lines | C | None | Manual item |
| Continued table heading on each continuation; LOT initial page only | — | NOT_IMPLEMENTED | Table continuation/linkage not robust | scope | Compare continuation pages and LOT | C | None | Pilot gap; manual review |
| Figures centered | P035 | AUTOMATED_PARTIAL | Geometry estimate | finding, scope | Inspect every figure | C,R | None | Retain |
| Figure description below figure, two blank lines | P017 | AUTOMATED_PARTIAL | Position and some spacing; exact blank lines uncertain | finding, scope | Inspect caption gap | C,R | None | Retain |
| Figure description sentence case, single spaced, left aligned | P017,P035 | AUTOMATED_PARTIAL | Body-caption case/spacing/alignment only partly checked | finding, scope | Check all caption properties | C,R,E | Later title-case guidance applies to List of Figures entries, not body captions | Keep body-caption behavior |
| Only Figure and number bold | — | MANUAL_REVIEW | Span-level font flags not reliable enough | scope | Inspect caption style | C | None | Manual item |
| Figure source below description in 10 pt if present | — | MANUAL_REVIEW | Source detection/context unreliable | scope | Inspect source lines | C | None | Manual item |
| Equation numbers chapter form X.x | — | NOT_IMPLEMENTED | Equations often raster/vector and hard to parse | scope | Inspect every equation | C | None | Manual pilot item |
| Equations centered; parenthesized number right aligned | — | NOT_IMPLEMENTED | Formula/page geometry not reliably identified | scope | Inspect placement | C | None | Manual pilot item |
| In-text Equation capitalized with matching parenthesized number | — | NOT_IMPLEMENTED | Cross-reference extraction not implemented | scope | Compare citations and equations | C | None | Manual pilot item |
| One appendix APPENDIX; multiple lettered A/B/C with title | P042,P063 | AUTOMATED_PARTIAL | Structural label patterns | finding, scope | Confirm number/order and titles | C,R | None | Retain |
| Appendix titles all caps in body and TOC | P042,P063 | AUTOMATED_PARTIAL | Some headings/entries detected | finding, scope | Compare both locations | C,R | None | Retain |
| Each appendix has short introductory paragraph | — | MANUAL_REVIEW | Content judgment | scope | Read first paragraph | C | None | Manual item |
| References consistently formatted in advisor-approved style | P064 | AUTOMATED_PARTIAL | Indentation/spacing only; advisor style unknown | finding, scope | Compare entries to agreed style | C,R | None | Manual item |
| Student names the reference style | — | MANUAL_REVIEW | Sheet has a student fill-in line | none | Fill in sheet with advisor-approved style | GSO sheet | None | Keep on official sheet |
| Student revises imported references for consistency | — | MANUAL_REVIEW | Process cannot be inferred from PDF | none | Review entries after import | GSO sheet | None | Keep on official sheet |
| Student attests checklist fulfilled | — | MANUAL_REVIEW | Personal attestation cannot be automated | none | Complete official sheet honestly | GSO sheet | None | Never auto-certify |
| Student acknowledges graduation-date impact of major errors | — | MANUAL_REVIEW | Institutional acknowledgement, not an audit check | none | Read/sign official sheet as required | GSO sheet | None | Never auto-certify |

## Ester feedback trace and rendered interface

| October 15 request | Current rendered behavior and evidence | Remaining action |
|---|---|---|
| Short, plain issue cards without repetition | PR #619 result cards show one short `student_summary`; note and rule ID are collapsed. Page is a single visible field when location permits. Synthetic HTTP card regression covers this. | Review long suggested fixes in a stakeholder session. |
| Color: blue clickable, red errors, green correct, neutral normal | Links/actions are blue; issue text and edge are red; confidence is neutral and labeled. No green pass state is invented because there is no verified pass result. | Add green only with a real positive check. |
| Meaningful labels | P011 shows MARGINS; other cards show category names, with secondary rule links. | Check category wording with students. |
| “Problem 1 of 150” navigation | The result and detail cards now use “Problem 1 of N”; filtering renumbers visible cards. | Confirm wording with stakeholders. |
| Bottom margin about 22 pt over | Measured P011 card gives side and overflow only when detector provides a finite positive measurement. | Preserve evidence gate. |
| Page once, clear check questions | Margin settings are “Needs review”; detected text crossing is “No.” The PDF cannot prove a source setting or a “Yes.” | Retain manual values and no unsupported yes. |
| Sorting, filters, links, highlights, responsive layout | Result page supports rule/category/page/confidence filters and sort. Synthetic browser and HTTP evidence is listed in external `RUN/TEST_RESULTS.md`; precise highlight requires a valid box. | Recheck on stakeholder sample. |
| Developer diagnostics | Rule ID and original finding number live in collapsed details; JSON developer export is separately labeled. | No default diagnostic leak found in reviewed cards. |

The live browser inspection used synthetic PDFs at 390, 768, and 1400 px. Each width showed two cards, a visible `Problem 1 of 2` label, and no horizontal overflow. Filtering to one page changed the label to `Problem 1 of 1`. The highlighted-page link and report download both returned PDFs. Screenshots and machine-readable route results remain in external RUN storage. The first version still showed a long margin correction; the final card now gives one short action and keeps the original correction in the expanded note.

## Report, limits, and readiness

The combined PDF keeps the uploaded pages and existing validated highlights, then appends a concise report. It now identifies the source filename and UTC audit date, counts findings and checklist-area scope, separates skipped checks and manual-only areas, lists the GSO area and secondary rule for each warning, gives physical PDF and printed labels when available, an expected-requirement summary, a student action, the complete correction detail when margin wording is shortened, and a highlight reference where supported. The companion text download uses the same finding identities. The report explicitly says that an absence of findings is not a verified pass, and that it does not replace the official sheet. It does not claim GSO approval. An independent CLI code review found three report issues (detector tolerance presented as a requirement, broad page/list mapping, and lost margin correction detail); all three were corrected and covered by focused tests.

Technical limits: PDF text extraction can miss scanned text, images, formulas and vector content; some locations lack a safe highlight; page classification and printed labels can be uncertain; broad coverage counts are static implementation scope, not per-document passed-requirement counts. The report explicitly labels verified passing requirements as **not measured**. Manual review is mandatory for subjective content, advisor style, committee metadata, exact source settings, and listed unimplemented items. The November pilot should pause if material false positives, unhighlighted critical errors, private-content leakage, or upload failures prevent a student from completing review. Historical adjudications must be replayed before expansion.

| Gate | Verdict | Direct basis |
|---|---|---|
| INTERFACE_READY | PASS | Synthetic rendered cards, filtering, keyboard link focus, and 390/768/1400 px layouts passed. Stakeholder acceptance is separate. |
| REPORT_READY | PASS | Synthetic route downloads and PDF readback show date, scope, requirement, actions, pages, and manual limits. Institutional acceptance is separate. |
| CHECKLIST_COVERAGE_DOCUMENTED | PASS | Every sheet requirement appears in the matrix above with limits and action. |
| END_TO_END_WORKFLOW_READY | PASS | Six valid synthetic classes completed upload/results/report/highlight routes; invalid inputs had readable errors. This establishes the synthetic workflow only. |
| OCTOBER_26_DEMO_READY | NOT ESTABLISHED | Demo script and synthetic workflow are prepared; meeting run-through pending. |
| NOVEMBER_BETA_READY | NOT ESTABLISHED | GSO case conflicts, Windows offline distribution, support and stakeholder acceptance remain open. |

Before 26 October: review this matrix and sheet conflicts with GSO/Ester; run the synthetic demo end to end on the actual meeting machine; confirm report readability and card noun with stakeholders; collect explicit feedback without treating merged code as acceptance. Do not present the offline Windows app or anonymizer as distributable until their independent work supplies evidence.
