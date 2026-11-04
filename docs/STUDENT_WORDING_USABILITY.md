# Student wording and evidence boundaries

These changes affect the website, shared desktop source templates, and
human-readable text, Markdown, and PDF reports. They do not change checks,
thresholds, raw findings, or the machine-readable report schema. Raw detector
remediation strings remain in JSON; student wording is a presentation layer.

## Checklist answers

A margin finding answers only the evidence-supported detection question:
“Did the check detect text crossing the bottom margin?” A known edge and finite,
positive overflow measurement support “Yes.” An unknown edge, missing distance,
zero/negative distance, or invalid value does not receive an automatic answer.
A finding's absence is never converted into a “Yes” about document compliance.

Questions about source-document margin settings always appear under **Check
yourself**, with instructions and no answer. PDF text positions cannot establish
Word/LaTeX margin settings. Landscape checks retain the recorded binding edge;
when that edge is unknown, students are asked to identify it themselves.
Images, drawings, and table rules still need manual inspection.

## Wording examples

| Before | After |
| --- | --- |
| “Is the left margin 1.5 inches? Needs review” | **Check yourself:** open page setup in the source document and check the left margin. |
| “Bottom margin exceeded by approximately 22.0 pt” | “Text appears to extend about 0.31 inch past the bottom margin boundary.” Exact points remain in Technical details. |
| “Set left margin to 1.5 inches and top, bottom, and right margin to 1 inch.” | Compare the marked text with the affected boundary. Adjust that text only if it crosses the boundary. |
| “Original finding 5” | **Technical details:** “Report reference 5 (matches PDF markers).” |

Multi-edge findings retain each detected edge and its measurement. Text crossings
are distinct from source margin settings. Conditional suggestions do not turn an
uncertain detection into a confirmed violation. Source/rule references and PDF
marker identities remain available.

The results page uses a short “How to use this report” section. Technical
navigation links use the same clickable styles as other enabled links. High
confidence is red, Medium amber, and Low gray, with text labels on both the main
list and drill-down pages. Confidence describes detection certainty, not severity.

## Desktop release status

The shared desktop source includes these wording changes, **pending a future
installer release**. No Windows build is part of this task. The already-published
Windows Beta **0.2.0-rc.3** executable is unchanged:

- File size: **41,326,578 bytes**
- SHA-256: `70713e44f18aaac32d5cc244aee3c82c7badbd8ce9d9dbf3b1dffe919a05f690`
- Build source: `b83c7c81cf4043a17eb45f7b4b2042e55bbe947a`

Do not overwrite that release or imply that website deployment changes its
installed executable. A future installer needs its own version and checksum.
About Us is now verified and implemented in shared source too; both changes await
the next desktop installer. See [About Us provenance](ABOUT_US_CONTENT.md).

The [rc.3 release record](releases/windows-0.2.0-rc.3.md) preserves the published build provenance. About Us (PR #646) and its acknowledgment correction (PR #647) also await the next installer.
