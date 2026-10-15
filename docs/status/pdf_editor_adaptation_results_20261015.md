# Existing PDF editor adaptation — synthetic experiment, October 15, 2026

**Decision:** The source-editing approach is technically promising for preserving
auditor behavior on these narrow synthetic fixtures, but it **requires redesign
and privacy review** before any confidential-document use. No real or embargoed
dissertation was read. This branch is experimental and must not be merged or
deployed as a student feature.

## Provenance and reproducibility

The auditor revision for every original/transformed comparison is the same
source tree based on main `4efd780dde53eea907a714df8bfed86e923ef86a`, with
the previous experiment commit `991e45bb06b8d8168a9da63f4274f3876ac21075`.
No detector, guideline, or historical judgment was changed. The previous full
suite completed: 4,775 passed, 6 skipped, exit 0. The precise failure
diagnosis appears in [the baseline diagnosis](pdf_editor_adaptation_diagnosis_20261015.md).

| Project | Inspected commit | License and dependency | Code/test findings |
|---|---|---|---|
| [pdf-edit-engine](https://github.com/AryanBV/pdf-edit-engine/tree/cee1d2cc042f84d0fb02c874765509c04a8624ac) | `cee1d2cc042f84d0fb02c874765509c04a8624ac` | MIT, © 2026 Aryan B V; Python ≥3.12; pikepdf, fontTools, pdfminer.six, lxml. Tested here as 0.2.0 with pikepdf 10.17.0, fontTools 4.67.0, pdfminer.six 20260107, lxml 6.1.3. | `find`/`replace` edit content streams and retain the original font; fidelity reports surface substitutions and overflow. Its own limitations exclude Form XObject text and some embedded-font cases. Its targeted `test_surgeon.py`/`test_find.py` run: 32 passed, 38 skipped because optional upstream corpus files were absent. It does not remove source metadata on our fixture without the adapter's cleanup. |
| [AnonPDF](https://github.com/pd95/AnonPDF/tree/27889e5e1e507cba84dd156f1c36ef9c2feebfad) | `27889e5e1e507cba84dd156f1c36ef9c2feebfad` | MIT, © 2026 AnonPDF contributors; `pypdf>=5,<7` (tested with 6.20.1). | Rewrites page and Form XObject text operands; output remains extractable. Its fixed `x` replacement changes widths considerably. It warns about metadata, annotations, attachments, tagged structures and other streams, but warnings are not fail-closed removal. No automated test suite was present in the inspected tree; `gen_fixtures.py` generates examples. |
| [sypht-team/pdf-anonymizer](https://github.com/sypht-team/pdf-anonymizer/tree/e9a6ddcee0fbf4130c4b9eaae8f9aadc1041f47d) | `e9a6ddcee0fbf4130c4b9eaae8f9aadc1041f47d` | MIT, © 2019 Sypht Pty Ltd; MuPDF `mutool`. | Replaces glyphs in a render device and writes each page as an image. The output has no usable text layer for this auditor. Its synthetic run failed with `TypeError: object is not callable` on local mutool 1.23.10. No automated tests were present. It is a visual reference, not an auditor baseline. |

No upstream code is vendored. The experimental adapters call a separately
installed pinned pdf-edit-engine package or AnonPDF script, and preserve the
upstream license/copyright attribution above. A fresh isolated environment can
be prepared with:

```bash
python -m venv /tmp/njit-pdf-editor-venv
/tmp/njit-pdf-editor-venv/bin/pip install -e .
/tmp/njit-pdf-editor-venv/bin/pip install \
  'git+https://github.com/AryanBV/pdf-edit-engine.git@cee1d2cc042f84d0fb02c874765509c04a8624ac'
```

Clone AnonPDF at the commit above into a scratch directory when testing its
fallback. Then run `python -m scripts.evaluate_pdf_editor_adaptation SCRATCH
--trials 5 --anonpdf-script PATH/anon_pdf.py --output RESULTS.json` with that
venv's Python. `scripts.probe_pdf_editor_privacy` creates planted synthetic
strings and checks ordinary extraction and PDF objects. Generated PDFs and JSON
belong in scratch, not the repository.

## Methods and geometry

The adapter accepts only small, title-marked `SYNTHETIC` PDFs with Base14,
horizontal ASCII text and the simple PDF object schema emitted by the fixture
generator. It rejects images, drawings, forms, annotations, links,
attachments, hidden layers, XMP, incremental history, invisible text operators,
unknown object structures and complex text runs. Each source
line is edited with pdf-edit-engine's `find`/`replace` API; every edit is checked
for success, original-font retention, overflow, reflow and missing glyphs. The
output is saved nonincrementally with generic metadata and regenerated trailer
IDs, then checked against the planned extractable text. Each text-show operand
must correspond to an extracted line at the same position and size. The marker
is user-editable and cannot prove that a PDF is safe to process.

Six methods were compared over five trials of each of the three original
synthetic fixtures (15 pairs per method, 190 source WARNING/FAIL findings):

| Method | Same findings at line anchor | Strict full-box matches | Lost / new under strict box | Maximum character-box drift | Text layer |
|---|---:|---:|---:|---:|---|
| Previous redraw, saved result | Not recorded | 37/190 | 153 / 24 | 0.196 pt | Yes |
| Previous redraw, rerun | 39/190 | 39/190 | 151 / 25 | 0.196 pt | Yes |
| Editor, full random | 41/190 | 34/190 | 156 / 26 | 63.348 pt | Yes |
| Editor, width-aware | 38/190 | 33/190 | 157 / 24 | 7.784 pt | Yes |
| Editor, generic structural markers | **190/190** | 175/190 | 15 / 15 | 5.328 pt | Yes |
| AnonPDF, fixed replacement | 55/190 | 30/190 | 160 / 30 | 48.704 pt | Yes |
| Redraw, same structural markers | 185/190 | 185/190 | 5 / 5 | 4.448 pt | Yes |

The saved 37/190 and fresh 39/190 differ because the random substitution is
not deterministic. The original-source count remains 190. The **line-anchor**
identity matches severity, rule, page, issue type, exact message for findings
without a box, and the box's left/top/bottom coordinates rounded to one point.
The strict identity also matches the right edge. The editor's 15 strict
nonmatches under the structural strategy are the same issues at the same line
anchors with changed right edges: five P011, five P017, and five P040. The
full-box drift is still a material layout difference and is not hidden by the
anchor comparison.

All tested methods preserved page dimensions, line and block counts, font names
and font sizes. Line starting coordinates, including paragraph indents and
vertical spacing, moved by **0 pt** in the editor outputs. The editor retained
the source span counts; per-character redraw changed span structure. Line right
edges moved by up to 5.328 pt with structural markers, 7.784 pt with
width-aware replacement, and 63.348 pt with full random replacement. Thus
original-font retention alone does not preserve text geometry.

The original fixtures cover a TOC, a List of Figures, page numbering, headings,
and a known left-margin crossing. An additional synthetic List of Tables
fixture is kept outside the 190-warning denominator: structural editing and
structural redraw each matched 10/10 original warnings at both identity levels;
full random and width-aware editing each matched 2/10, and AnonPDF 3/10.
Matching warnings on these small fixtures does **not** mean all project rule IDs
are compatible or that the warning itself is correct. Only the intended margin
crossing was hand-verified as a formatting defect.

## Per-rule finding compatibility

Counts are five-trial **line-anchor matches**. The previous saved baseline used
the stricter full-box signature, so its column is contextual rather than a
like-for-like location comparison. Complete per-rule strict and anchor counts,
including lost and introduced findings, are emitted in `RESULTS.json`.

| Rule | Original | Saved baseline | Editor random | Editor width | Editor structural | AnonPDF | Structural redraw control |
|---|---:|---:|---:|---:|---:|---:|---:|
| P011 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| P013 | 50 | 32 | 34 | 33 | 50 | 50 | 50 |
| P014 | 15 | 0 | 0 | 0 | 15 | 0 | 15 |
| P017 | 10 | 0 | 0 | 0 | 10 | 0 | 10 |
| P019 | 10 | 0 | 2 | 0 | 10 | 0 | 10 |
| P022 | 5 | 0 | 0 | 0 | 5 | 0 | 5 |
| P025 | 10 | 0 | 0 | 0 | 10 | 0 | 10 |
| P031 | 10 | 0 | 0 | 0 | 10 | 0 | 10 |
| P038 | 50 | 0 | 0 | 0 | 50 | 0 | 50 |
| P040 | 10 | 0 | 0 | 0 | 10 | 0 | 10 |
| P063 | 5 | 0 | 0 | 0 | 5 | 0 | 0 |
| P085 | 10 | 0 | 0 | 0 | 10 | 0 | 10 |

The marker policy preserves only exact generic headings, chapter/appendix
labels, figure/table entry prefixes, page folios, and the generic words
“thesis”/“dissertation”; titles, names, research terms and captions are
replaced. This restores text-dependent detector context and is responsible for
most of the gain. The matched structural redraw control proves the gain is **not
principally from the upstream engine**. The engine does retain spans and the
P063 appendix warning that redraw lost, while its width drift prevents 15
strict box matches that redraw kept. No auditor code was changed.

## Content inspection and limits

A separate generated PDF planted four synthetic identifying/topic strings in
page text and metadata. For full random, width-aware, structural editor output,
and AnonPDF output, none of the planted strings appeared in PyMuPDF or pypdf
extraction, raw output bytes, decoded PDF objects/streams, or metadata. The
outputs had zero attachments, images, annotations and hidden layers, one EOF
marker, and blank author fields. Adversarial review also found recoverable text
in source author metadata, marked-content `/ActualText`, compatibility sections,
unextracted text-show operands, font resource maps and encoding dictionaries,
page-tree fields, inline catalog metadata, and the trailer ID. The adapter now
rejects the unsupported content and object forms, reconciles all text-show
operands with extracted glyphs, clears metadata, and replaces trailer IDs.
Synthetic regressions cover each reported case. These fixes are narrow and do
not establish comprehensive PDF sanitization.

This is **not a confidentiality assessment**. Every output retained the exact
source word-length pattern. Punctuation, line breaks, folios, generic headings,
font identities, and document structure remain; an adversary with outside
knowledge could use them to narrow or infer content. Unrecognized PDF encodings,
hidden content, fonts, layers, or viewer-specific behavior are not proved safe.
The structural strategy intentionally retains generic readable words, so an
ordinary “no original words remain” claim would be false. Full source text might
also be reconstructable through width/position fingerprinting on a richer
document. The strict preflight narrows the experiment; it does not certify an
arbitrary PDF or a user-edited `SYNTHETIC` marker.

## Engineering recommendation

Continue only as an offline synthetic research prototype. A useful next step
would be a per-rule compatibility contract that separates content-dependent
checks from geometry-only checks, followed by adversarial privacy assessment
and institutional approval of any document handling. An offline complete
auditor, run where the dissertation already resides, may satisfy the underlying
privacy need with less information leakage than sharing any transformed PDF.
The current code and evidence are not appropriate for real student documents.
