# Local PDF content anonymizer

The `anonymize` command replaces extractable, substantive PDF text with seeded
synthetic characters and keeps generic thesis labels, numbering, typography,
and page geometry where the supported PDF structures permit it. The result is
a **content-anonymized PDF with formatting preserved**. It does not guarantee
that the source cannot be inferred from the remaining layout, word lengths,
punctuation, headings, or other context.

Use Python 3.12 or newer for the pinned editor. Install the optional
dependencies and work with a new output path:

```bash
python -m pip install -e '.[anonymizer]'
anonymize original.pdf -o anonymized.pdf --authorized-local-input
anonymize original.pdf --output-dir ./outputs --authorized-local-input \
  --seed 42 --strategy width --verify-auditor --report ./outputs/check.json
```

For a local file picker, install a Python build with Tkinter and run
`anonymize-gui`. Select the source PDF, then choose a **new, separate** output
path. The picker calls the same anonymizer with the auditor compatibility check
enabled. It displays a refusal when the PDF or destination is unsupported. It
does not start a server or upload the file. On Windows, a one-folder build can
be prepared with `python -m pip install -e '.[anonymizer]' pyinstaller` followed
by `pyinstaller --noconfirm packaging/anonymizer_gui.spec`; the spec is a build
recipe, not a tested Windows executable. The picker runs synchronously, so its
window may be unresponsive while a large PDF is processed.

**Distribution licensing:** PyMuPDF is available under AGPLv3 or a commercial
license. Review the applicable license obligations before distributing a
packaged anonymizer; this branch does not provide a redistribution clearance.
The pinned editor is MIT and pikepdf is MPL-2.0. See the
[PyMuPDF licensing page](https://pymupdf.io/licensing).

`--authorized-local-input` confirms that you have permission to process the
document locally. There is no title marker requirement. No document bytes are
sent to a service by this command. The input is never overwritten; an existing
output is refused. The PDF is staged beside the requested destination and only
published after content and geometry checks pass. A refusal leaves no partial
destination. `--report` writes a JSON result or a refusal reason without
including source body text. Keep the report and output in a location
appropriate to the document's sensitivity.

The default `width` strategy samples replacement characters whose glyph
advances keep the original line close. `random` gives a broader seeded choice
while still enforcing the same geometry checks. `--seed` reproduces extracted
replacement text across processes. The full PDF bytes can differ because the
fresh writer creates new document identifiers. `--verify-auditor` compares
non-PASS rule IDs, issue types, physical pages, severity, confidence, selected
classification fields, and highlight geometry with the input. It can refuse a
PDF if substantive text affects a finding. `--verify-fidelity` names the
mandatory geometry/content checks and is always enabled; `--verbose` prints
progress without printing source text.

## Supported scope

- Searchable, horizontal text PDFs with Base14 or usable embedded TrueType
  fonts; several tested DejaVu subset fonts can be redrawn from an exact
  locally installed full font. Unicode letters and digits work when a usable
  glyph exists; mathematical operators and punctuation are generally retained.
  Mixed bold/italic spans, ordinary paragraphs, page
  numbers, TOC/list labels, captions, references, indents, and two-column
  examples are covered by synthetic tests.
  Superscript and subscript digits are replaced only with glyphs in the same
  notation class when the font supports them; mathematical operators and
  punctuation remain visible and can disclose subject matter.
- MediaBox, CropBox, landscape pages, and page rotation are preserved in
  accepted PDFs. Up to 250 pages and 100 MB are admitted; those bounds are
  safety limits, not a performance guarantee.
- Simple, nonoverlapping raster figures of sufficient size are replaced with
  a visible synthetic image placeholder in the same occupied region. The
  original image stream is removed. This does not interpret charts or diagrams.

The command refuses scans without searchable text, Form XObjects, vector
drawings, text layered over an image, small image regions, annotations and
comments, links, attachments, forms, tags, hidden or translucent text,
unextractable glyphs, unusual text transforms, optional layers, complex
graphics states, page print boxes/UserUnit, unknown page-tree data, and other
unverified PDF structures. It reports the first unsupported feature. A font
subset without a usable local full font is refused. On refusal, simplify or
re-export the source through a trusted local tool and review that new source
before trying again; do not assume a PDF reader's visual appearance proves
that hidden content is absent.

The output is searchable in tested PyMuPDF, pypdf, Poppler, and MuPDF readers.
Formatting preservation is measured with page boxes, fonts, span and line
counts, baselines, spacing, line ends, and character boxes. Independent
synthetic validation and remaining limits are in the
[development report](../status/practical_pdf_anonymizer_development_20261016.md).
