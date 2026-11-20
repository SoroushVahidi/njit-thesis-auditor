# F30: bounded cross-page figure descriptions

Base: `d703b1266077cdd4fb5b5aa71c9f30011179384f`.

P017 previously evaluated a page-local caption fragment as a complete description.
The caption parser joined only following lines in the same text block. It could
therefore recommend punctuation at a page break, even when the description ended
correctly on the next physical PDF page. A separate first-line multi-sentence
prose safeguard also excluded one corroborated panel description.

## Recognition and scope

`pdf_caption_continuations.py` provides an opt-in logical-caption path for P017
and P088. Other layout, font, body-spacing and body-reference consumers retain
the existing page-local parser. The source PDF model is not mutated.

Association requires adjacent physical pages, a nearby graphic above the caption,
matching typography and left edges, a caption reaching the last body-text line
near the first page's bottom, and compatible text near the next page's top.
The text must also provide continuation structure: an explicit matching continued
label, an incomplete parenthesis/connecting phrase, or corresponding panel
positions. A page break or missing punctuation alone is insufficient.

Each fragment retains its physical page, source lines and local bounding box.
Printed document page labels are recorded only when a unique centered numeric
footer supplies them; physical page indices never stand in for printed labels.
The original caption anchor remains the figure identity. A supported repeated
continued label is consumed as part of that identity, preventing a false P088
duplicate without suppressing genuine independent duplicate labels.

The first-line multi-sentence safeguard remains active in the legacy parser.
Recovery requires panel-description structure plus the graphic and cross-page
association evidence. This does not generally classify multi-sentence prose as
captions.

Joins stop at headings, new captions, source notes and resumed prose. Changes in
font, alignment, parallel columns, rotation or vertical text cause abstention.
A same-margin, same-font paragraph immediately after an unlabeled tail also
causes abstention because its endpoint is ambiguous. Ambiguous cases retain existing page-local behavior.

## Punctuation and reporting

P017 evaluates the reconstructed logical end. A real missing-punctuation finding
retains its warning severity and high confidence but targets the final line on
the continuation page. Its preview and primary highlight refer to that same line.
Separate start/end page, printed-label and bbox metadata preserve provenance;
boxes from different pages are never unioned or sent to one page's highlight
renderer. Shared student-facing context names both pages and explains that the
highlight target is the final line only. Other highlighting behavior is unchanged.

No standalone F30 warning or new rule ID is introduced. The supplied NJIT WIP
formatting guidance permits marked multi-page figures/tables, and the finding
model has PASS/WARNING/FAIL rather than an informational severity. Recognition
alone does not establish a violation. Reporting accidental splits versus permitted
continuations remains a policy decision; this work does not invent a prohibition.
F29 table continuity and all unrelated layout/spacing work remain outside scope.

## Verified original cases and comparisons

Private originals were read in place; no manuscript text or binaries are added
to fixtures. The Chao source hash and original review hash match the earlier audit.

| Figure | Physical pages | Printed pages | Recognized source lines | Result |
|---|---|---|---|---|
| 2.6 | 47–48 | 25–26 | 3 + 1 | False P017 punctuation finding removed |
| 4.2 | 113–114 | 91–92 | 3 + 8 | Punctuation evaluated at the complete end; false finding removed |
| 5.4 | 159–160 | 137–138 | 7 + 4 | Guarded panel-caption recovery; complete description recognized |

| Authorized document | Raw before → after | Visible before → after | P017 before → after |
|---|---:|---:|---:|
| Chao | 306 → 304 | 59 → 57 | 9 → 7 |
| Oscar | 445 → 445 | 205 → 205 | 3 → 3 |
| Praneeth | 216 → 216 | 103 → 103 | 1 → 1 |

Only Chao's original student finding IDs `f84` and `f156` are removed. These IDs
were positional: 16 surviving cards are renumbered after the removals. No surviving
raw finding, classification, confidence, severity, source box or page reference
changes. The other two documents' raw findings and student cards match exactly.
There are no added findings or F30 advisories. Private hashes, fingerprints, ID
mappings and comparison outputs remain in task notes outside Git.

## Validation and limitations

Synthetic tests exercise one-line/code-leading and multi-line continuations,
period-ending first fragments, incomplete logical ends, genuine missing periods
near page boundaries, structural/prose/source-note exclusions, ambiguous geometry,
nonadjacent/empty/last pages, panel recovery and true versus continued P088 labels.
Real web/JSON/Markdown/standalone and web text/original/highlighted/combined-PDF
paths verify accurate page references and source-page-only annotation geometry.

Targeted validation passed: 35 F30 tests; 1,389 caption/layout/registry and
cross-rule tests (including the F30 tests); 485 report/rendering tests; and
157 adjacent-rule tests. These selections overlap and are not an additive suite
total. Ruff passed, and mypy found no issues in 166 source files.

The full nonconfidential suite is a separate final-candidate gate; targeted test
results are not a claim that this gate has completed.

Recognition intentionally covers only one adjacent page break, at most 24 lines
per fragment, measured portrait text and a corroborating raster graphic. Vector-
only figures, unsupported typography, additional page breaks and ambiguous prose
remain unjoined. P026/P055 and the separate P020/P023 bands remain page-local;
this task adds no new caption exemptions in those rules. Existing same-page
prose guards are preserved. Policy-dependent split advisories are deferred.
The November 20 audit's 213-item classifications remain historical, not a new
audit or a claim that all email-feedback work is closed.
