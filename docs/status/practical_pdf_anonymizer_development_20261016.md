# Practical PDF content anonymizer development — October 16, 2026

## Scope and provenance

This work began at `b63920f2675eca09098069f16af04d64a0031851`, the
unchanged head of [PR #623](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/623).
The experimental CLI and synthetic fixtures from the October 15 and 16
[adaptation](pdf_editor_adaptation_results_20261015.md) and
[reuse study](pdf_anonymizer_reuse_and_prototype_20261016.md) were inspected.
The later privacy commit `f017bb4ca0d12cd0ebd4b29d634ce94a7292db55`
was read without changing its worktree. Its useful degradation-reporting gate
was carried forward proportionally: every upstream warning is recorded, while
the final geometry/content/auditor criteria decide whether a warning is
material. Upstream errors, font substitution, and reflow are refused.
The accepted matrix recorded one `overflow_detected:warning` and one
`overflow_shift_clamped:warning`; neither exceeded the measured final
geometry or auditor limits.

The implementation uses
[pdf-edit-engine 0.2.0 at cee1d2cc](https://github.com/AryanBV/pdf-edit-engine/tree/cee1d2cc042f84d0fb02c874765509c04a8624ac)
(MIT) for content stream editing and font lookup. It uses pikepdf 10.17.0
(MPL-2.0) for a fresh full-file rewrite, PyMuPDF 1.28.2 (AGPL/commercial)
for extraction/rendering and the subset/image redraw, pypdf 6.21.0
(BSD-3-Clause) for independent syntax and extraction, fontTools 4.67.0,
pdfminer.six 20260107, and lxml 6.1.3 through upstream dependencies.
No upstream code was vendored. Atelier PDF was reviewed as a possible
operator/font implementation, but its tested metadata behavior would need
the same cleanup and its code was not imported. The existing editor already
handles searchable content streams and reports fidelity; the local fallback
is restricted to cases it cannot reliably edit. License review is needed
before distributing a product with PyMuPDF.

The installed CLI is documented in the
[usage guide](../features/practical_pdf_anonymizer.md). It removes the
literal `SYNTHETIC` title gate in favor of an explicit local-authorization
flag. The anonymizer itself was exercised only on generated PDFs. An
unrestricted repository pytest run inadvertently exercised tests that read an
existing real review-sample PDF. That run is excluded from the synthetic-only
validation claim. A subsequent validation copy under the private run directory
contains only two established synthetic web-demo PDF fixtures and no raw-data
directory. No real dissertation was passed to the anonymizer, transmitted, or
committed. No production service or detector rule was changed.

## Implementation and acceptance limits

The tool admits verified catalog, page-tree, page, and resource dictionaries
and reconciles extracted text with traced glyphs. It replaces every planned
span, checking the rendered result against its exact replacement. Generic
structural labels and numbering remain; substantive names, titles, prose,
reference titles, and research descriptions change. The `width` and `random`
strategies both use a seed and an original-font glyph-width search; candidate
ordering is stable across Python hash seeds. Unknown content is refused rather
than silently retained. Simple raster figures become labeled synthetic
placeholders; their original image streams are absent from output.

The acceptance gate requires the same page count/order, MediaBox/CropBox,
rotation, text block/line/span/character counts, font family/style/size,
line starts within 1 pt, line ends within 4 pt, and independent-parser
searchability. Character-box drift must remain within 5 pt at the 95th
percentile and 8 pt at the maximum. It also checks text color, every planned
replacement, raw and decoded objects, metadata, both regenerated trailer IDs,
residual structures, old image stream hashes, and a single EOF marker.
Optional auditor matching compares stable finding
attributes including all four bbox coordinates, confidence, selected
classifications, and highlight geometry at 0.1 pt precision. The output is
published only after verification. The input is never overwritten.

UserUnit and print boxes, partial text opacity, arbitrary graphics state,
forms, Form XObjects, vector drawings, scans, hidden text, annotations,
attachments, tags, links, unusual transforms, and unknown object properties
are refused. A subset without a usable local font is refused. Substantive
nontext content other than sufficiently large simple raster images is not
replaced. No claim of unlinkability is made. The exact word-length and
layout pattern is retained by design; this can reveal information.

## Synthetic validation

The final 34-case matrix attempted 21 accepted and 13 refused PDFs. Accepted
cases cover 66 pages, 290 text spans, up to five font families in one case,
Base14 and embedded Unicode/math, subset fonts, mixed bold/italic spans,
multiline paragraphs, TOC/list labels, headings, captions, references,
hanging/first-line indents, columns, landscape/crop/rotation, and a raster
figure. The 13 refusals each identified a specific unsupported structure;
none published a PDF. They included annotations, XMP/attachments/layers,
vector content, transformed/hidden text, a scan, a Form XObject, action,
tagged structure, thumbnail, and AcroForm. Focused regressions additionally
refused page-tree metadata, custom page-tree data, custom font/Unicode-map
and content-stream data, UserUnit, TrimBox, and translucent text. These
fixtures are not a representative sample of all academic PDF generators or
rule IDs.

Across the accepted matrix, page dimensions/order, fonts, style flags,
size, spans, baselines, adjacent spacing, and line starts matched. Maximum
line-end movement was 0.096 pt; maximum character-box drift was 4.884 pt
(maximum per-case 95th percentile 4.268 pt). Seven selected 72 dpi page
renders had zero changed pixels outside the union of text and image regions
expanded by 3 pt. That image-mask check does not prove visual equivalence
inside text regions. The raster fixture's planted image text was recovered
from the source by OCR and was absent from OCR of the synthetic placeholder.

The unchanged NJIT auditor matched 323/323 non-PASS findings over 23 accepted
source/output pairs, spanning 15 rule IDs: zero lost or introduced, zero
confidence/classification/highlight mismatches, and zero reported bbox delta
at auditor precision. The separately planted synthetic ground-truth page
preserved its deliberate margin and heading/spacing findings; its small body
font was not flagged by this auditor, so that case cannot establish font-rule
recall. Auditor equivalence here is a measured compatibility result, not a
claim that all findings are correct or all 86 rule IDs are covered.

On 18 width-strategy accepted outputs, PyMuPDF, pypdf, Poppler `pdftotext`,
and MuPDF `mutool` all extracted searchable text. None recovered a tested
nonstructural source word of at least five letters or a planted source token.
Pikepdf object scans, raw bytes, and metadata checks found no planted token
or identifying metadata; all 18 had one EOF marker. Pypdf emitted warnings
about odd Unicode CMap data on some accepted embedded-font PDFs, but its
extracted output tokens agreed with PyMuPDF. Fresh rewriting removed planted
old incremental revisions and orphan objects in the accepted variants.

A separate 100-page, 400-span generated PDF completed in 15.309 seconds,
matched 102/102 auditor findings, and moved its furthest line end 0.022 pt.
Repeated text still requires sequential upstream edits when ambiguous, so
time can grow with repeated spans; the implementation releases prior scratch
PDFs as it proceeds. The 100 MB/250-page caps are admission bounds, not a
promise of linear runtime. All generated PDFs, reports, and verbose evidence
are in the untracked run directory. No `anonymize-*` scratch directories
remained there after validation, and the refused cases left no destination
PDFs.

## Validation and review

The focused suite covers embedded and subset fonts, Unicode/math, page
geometry, simple images, authorization/CLI, degradation events, long PDFs,
source-content cleanup, seed stability across processes, partial-edit
rejection, and unsupported structures. Exact final command outcomes are in
`RUN/TEST_RESULTS.md`; the run directory is outside Git. The unrestricted
full pytest result is recorded there as a process deviation, not as the
mission's privacy-compliant gate. A full run in the synthetic-only copy had
4,804 passed, 22 skipped, and seven failures caused by absent real PDF/XLSX
fixtures or the sample-dependent home page. Those seven are deselected in a
second synthetic-only run: 4,804 passed, 22 skipped, seven deselected, three
warnings, exit 0 in 74.96 seconds.
An independent read-only code review found
two high and five medium issues. The high issues
(page-tree metadata retention and a surviving mixed-span edit) were fixed and
regressed. The medium geometry, opacity, seed, auditor-comparison, and scratch
disk issues were addressed or bounded as described above. The remaining
sequential-edit performance limit is documented here. This review was code
review, not an independent confidentiality or legal assessment.

An additional local adversarial probe found a retained custom field in an
otherwise valid font dictionary; explicit font and stream dictionary
validation now refuses this case and has focused regressions.

An object-level check also found that the PDF writer's default preserved the
source's first trailer ID. The tool now replaces both IDs and rejects any
source/output ID overlap; a synthetic regression covers it.

## Practical decision

The CLI is usable locally for authorized **searchable text PDFs within the
documented grammar**, with simple raster figures, and reports a specific
reason when it cannot process a source. It is not a general PDF sanitizer and
does not guarantee unlinkability. Broader generator/font coverage, more
complex figure and diagram handling, and adjudicated tests across additional
auditor rules are the next work if needed. No merge or deployment is part of
this branch.
