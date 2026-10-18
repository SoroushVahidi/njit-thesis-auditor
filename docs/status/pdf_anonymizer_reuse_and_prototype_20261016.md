# Reuse-first, format-preserving PDF replacement prototype — 2026-10-16

**Decision: REVISE as a synthetic research prototype; NO-GO for confidential dissertations or shareable transformed PDFs.** The local CLI works on a tightly restricted class of generated PDFs. Its positive format, auditor and planted-token results do not establish anonymity or safety to distribute an output. No real dissertation or raw LaTeX was processed, uploaded, logged or committed. The public web service and offline desktop application were not changed.

## October 15 recovery

The first experiment is commit `991e45bb06b8d8168a9da63f4274f3876ac21075` on `experiment/format-preserving-text-20261015`, in the `format-preserving-text-20261015` worktree. Its project-owned files are `src/njit_auditor/experimental_pdf_text.py`, `scripts/generate_synthetic_obfuscation_fixtures.py`, `scripts/evaluate_synthetic_obfuscation.py`, `tests/test_experimental_pdf_text.py` and the [October 15 proof-of-concept report](synthetic_pdf_text_replacement_poc_20261015.md). Per-character redraw held source positions and fonts but replaced headings, folios and list labels the auditor uses. The saved five-trial result was 37/190 strict warning matches, 153 lost and 24 new. Random draws explain small differences across replays.

The follow-on commit `c8cf75095394084887b89dfe8b3fa534cbcf4f9f` on `experiment/pdf-editor-adaptation-20261015`, in the `pdf-editor-adaptation-20261015` worktree, added `scripts/experimental_pdf_engine_adapter.py`, `scripts/evaluate_pdf_editor_adaptation.py`, `scripts/probe_pdf_editor_privacy.py`, tests and [diagnosis](pdf_editor_adaptation_diagnosis_20261015.md)/[results](pdf_editor_adaptation_results_20261015.md). It adapted [pdf-edit-engine](https://github.com/AryanBV/pdf-edit-engine/tree/cee1d2cc042f84d0fb02c874765509c04a8624ac) v0.2.0 and retained only generic structural markers. The archived result was 190/190 line-anchor matches and 175/190 full-box matches. Our independent one-trial replay produced 38/38 anchors and 35/38 full boxes, with up to 5.328 pt line-right drift. The structural-redraw control had similarly strong auditor results, showing that retained generic markers drove most of the gain. The editor retained source spans, but its unbalanced replacement widths caused the 15 strict box mismatches. Privacy and re-identification remained unresolved.

Both October 15 commits were cherry-picked into this isolated development branch. Their existing experiment code was extended; no PDF engine was newly implemented and no upstream source was vendored. Original experiment worktrees were read only.

## Reuse research and selection

The exact `HEAD` revisions below were checked on 2026-10-16. Repository source, tests, known limits, releases, issues, dependencies and licenses were considered. A more detailed feature/privacy/performance matrix is held with private run evidence. Sources: [pdf-edit-engine README and limits](https://github.com/AryanBV/pdf-edit-engine), [AnonPDF](https://github.com/pd95/AnonPDF), [atelierPDF](https://github.com/Lomchat/atelierPDF), [Sypht PDF anonymizer](https://github.com/sypht-team/pdf-anonymizer), [pikepdf](https://github.com/pikepdf/pikepdf), [PyMuPDF](https://github.com/pymupdf/PyMuPDF), and [anon-pii](https://github.com/tcheuD/anon-pii).

| Candidate | Exact revision, license | Relevant result and limit |
|---|---|---|
| pdf-edit-engine | `cee1d2cc042f84d0fb02c874765509c04a8624ac`, MIT, v0.2.0 | Tested Tj/TJ editing and original-font retention; extensive upstream tests. Does not edit Form XObject text or sanitize hidden structures. Its documented subset-font support is broader than this prototype's accepted grammar. Chosen for continuity with the October 15 adapter. |
| AnonPDF | `27889e5e1e507cba84dd156f1c36ef9c2feebfad`, MIT | Edits streams and Form XObjects, but fixed `x` replacement yielded 30/190 strict matches and 48.704 pt maximum character drift in the prior test. Warns about several hidden structures rather than removing all. |
| atelierPDF | `ecece75faacaec08aa00b402351358963f07c9ef`, MIT | Strong operator/font and pixel-verification engine. Given our balanced replacement payload, matched 67/67 strict findings on five synthetic fixtures. It retained planted original title/author in metadata, decoded objects and raw bytes. Its hosted flow stores uploads and records usage; no hosted path was used here. |
| Sypht PDF anonymizer | `e9a6ddcee0fbf4130c4b9eaae8f9aadc1041f47d`, MIT | Rasterizes and loses the auditor text layer; prior local mutool run failed. Last push observed in 2019. |
| pikepdf | `b8ee8f0388373325e43873ede541758020253ad1`, MPL-2.0 | QPDF-backed object parser/full writer. Used for fresh output and independent object inspection; does not supply semantic text replacement or anonymity. |
| PyMuPDF | `b8904b27efa0c4e2258f0e46ab4498a6173ffa22`, AGPL-3.0 or commercial | Used for extraction/rendering and metadata cleanup. Redact/reinsert or per-glyph redraw does not inherently retain auditor semantics or source font/span structure. |
| anon-pii | `270b2b1d69ffcdc5c6d4d83ba11e73f1890a5f7d`, MIT | Actively maintained PII/redaction candidate, but its own PDF mode remains experimental and does not demonstrate thesis-format auditor equivalence. |

The selected editor is installed separately at v0.2.0 from the pinned revision. It depends on pikepdf, fontTools, pdfminer.six and lxml; the validation environment used pikepdf 10.17.0, PyMuPDF 1.28.2, pypdf 6.20.1, fontTools 4.67.0, pdfminer.six 20260107 and lxml 6.1.3. MIT attribution applies if upstream code is redistributed; MPL-2.0 notices and modified-file terms apply to pikepdf; PyMuPDF/MuPDF's AGPL/commercial terms require review before distribution or network deployment. This experimental branch is neither distributed as a product nor deployed. No upstream source was copied.

## Prototype architecture

The [local CLI](../../scripts/experimental_pdf_anonymizer.py) is a separate experimental script. It requires a new output path, accepts a deterministic integer seed for replacement text in synthetic tests, stages files beside the destination, and atomically links the PDF into place only after all gates pass. Fresh random trailer IDs mean byte-for-byte PDF output is intentionally not seeded. It blocks ordinary Python socket connections during processing. The [adapted editor](../../scripts/experimental_pdf_engine_adapter.py) uses pdf-edit-engine `find`/`replace` on the original Tj/TJ operands. A bounded beam search chooses different Base14 glyphs to minimize cumulative line width while favoring similar per-glyph widths. The original font resources, text matrices, line starts and spans remain. The source is never overwritten.

Preflight accepts only small, title-marked `SYNTHETIC` PDFs with a fully accounted-for object graph and horizontal ASCII text using seven verified Base14 aliases (`helv`, `hebo`, `tiro`, `tibo`, `tiit`, `cour`, `cobo`); every text show must reconcile with extracted text. It rejects encryption, incremental history, duplicate/unindexed objects, forms, Form XObjects, annotations, attachments, links, images, drawings, scans, tags, optional layers, XMP, actions, embedded/subset fonts, complex encodings, Unicode/math, rotated/cropped pages, rotated matrices, mixed-font lines, invisible text and unknown operators. Limits are 12 pages, 30,000 glyphs, 2,048 PDF objects and 5 MB. The marker is user-editable and does **not** verify that a PDF is synthetic or nonconfidential.

The wrapper performs a full rewrite, clears Info fields, replaces trailer IDs, checks page/line/font geometry and reruns the unchanged auditor. Strict finding matching compares rule, physical page, issue type, severity and all four rounded bbox coordinates as a multiset; unboxed message text is digested only in memory. It also checks PyMuPDF, pypdf, Poppler and MuPDF extraction; pikepdf and PyMuPDF decoded objects; raw bytes; metadata; residual structures; and planted-token representations. A failure leaves no destination PDF. JSON diagnostics contain counts, geometry and rule IDs, not source body text. `SYNTHETIC_TECHNICAL_GATES_PASSED` is deliberately not a sharing or confidentiality verdict.

## Three measured outcomes

### A. Format fidelity

In the final seeded evaluation, 18 balanced pairs covered six synthetic fixture families: three historical text layouts plus a List of Tables, an extended five-page thesis with paragraphs, captions, references and a deliberate margin violation, and a two-column text page. Across 43 compared pages, MediaBox/CropBox/page order, 208 blocks, 225 lines, 5,906 characters, 225 line font/size signatures and 225 span counts matched. Line left/top/bottom, baselines and adjacent line spacing moved 0 pt. Line-right drift had median 0 pt, 95th percentile 0.000031 pt and worst 0.031982 pt. Per-character maximum-axis box drift had median 0 pt, 95th percentile 1.554 pt and worst 3.520 pt. Six representative pairs had zero changed pixels outside masked text areas at 72 dpi. The render mask is not a glyph-validity or privacy proof.

### B. Auditor equivalence on these fixtures

The final comparison used the same auditor revision `4efd780dde53eea907a714df8bfed86e923ef86a` for both source and output. It measured WARNING/FAIL findings, not their correctness. The seeded historical denominator was 190 findings over 15 pairs:

| Method | Strict matches | Lost | New | Anchor matches |
|---|---:|---:|---:|---:|
| October 15 random redraw, seeded replay | 39/190 | 151 | 29 | 39/190 |
| October 15 structural editor | 175/190 | 15 | 15 | 190/190 |
| Balanced gated prototype | **190/190** | **0** | **0** | **190/190** |

Including supplemental fixtures, balanced editing matched **221/221** findings with zero lost/new. The structural editor matched 205/221, losing and introducing 16 each under strict boxes; the old redraw matched 43/202 on the 17 pairs it completed and refused the extended fixture. The full comparison emitted findings from only 13 rule IDs. P011, P017 and P040 strict mismatches under structural editing were associated with right-edge geometry. Named heading/folio/list and chapter/appendix rules depend on readable generic markers; the October 15 diagnosis and redraw control establish that geometry alone is insufficient. The only hand-verified defect in the historical fixtures is the deliberate left-margin crossing. Other findings are fixture outputs, not reviewer truth. The many unexercised rule IDs and real-document language remain untested.

### C. Technical removal and re-identification

A planted synthetic text/metadata fixture contained four artificial secrets. None was recovered from the balanced output by PyMuPDF, pypdf, Poppler `pdftotext`, MuPDF `mutool`, pikepdf/PyMuPDF object scans, metadata or raw bytes. On the 18 evaluated pairs, no nonstructural source word of five or more letters remained extractable, no non-generic source line remained in decoded/raw objects, and no attachments, images, annotations, forms, XMP, layers, extra catalog/page/trailer keys or residual object definitions remained. Twenty-one of 23 hostile-source variants were refused with no output; the two accepted variants were ordinary text-only PDFs. Tesseract recovered planted source secrets from pixel imagery and a full scan, and a vector-path decoder recovered a planted source barcode; the prototype refused each source. A complete CLI run traced with `strace -f -e trace=network` made no network system call.

**These observations do not establish anonymization.** All 18 accepted balanced outputs preserved the exact source word-length sequence, alongside punctuation, typography, layout, generic headings and folios. That information can fingerprint text or narrow candidate documents. In a six-candidate synthetic linkage check using only page sizes and line boxes rounded to 1 pt, all 18 outputs uniquely matched their source fixture; this does not quantify real-world re-identification risk. Unknown PDF encodings/objects and viewer behavior are unexamined. No private dissertation was used to test the output, and no transformed PDF is approved to share.

## Reproduction and validation

Use only generated PDFs. The local environment needs Python 3.12+, `pdftotext` and `mutool`. For example:

```bash
python3.12 -m venv /tmp/njit-anonymizer-venv
/tmp/njit-anonymizer-venv/bin/python -m pip install -e '.[dev]'
/tmp/njit-anonymizer-venv/bin/python -m pip install \
  'git+https://github.com/AryanBV/pdf-edit-engine.git@cee1d2cc042f84d0fb02c874765509c04a8624ac'
PYTHONPATH=src:. /tmp/njit-anonymizer-venv/bin/python \
  -m scripts.generate_anonymizer_adversarial_fixtures /tmp/njit-anonymizer-fixtures
PYTHONPATH=src:. /tmp/njit-anonymizer-venv/bin/python \
  -m scripts.experimental_pdf_anonymizer \
  /tmp/njit-anonymizer-fixtures/synthetic_extended_thesis.pdf \
  /tmp/njit-anonymizer-fixtures/replaced.pdf --seed 42 \
  --report /tmp/njit-anonymizer-fixtures/diagnostics.json
PYTHONPATH=src:. /tmp/njit-anonymizer-venv/bin/python \
  -m scripts.evaluate_anonymizer_prototype /tmp/njit-anonymizer-eval \
  --trials 5 --output /tmp/njit-anonymizer-eval.json
```

Focused experiment tests and the full repository gates validate source behavior; private generated reports/PDFs are excluded from commits. An independent tool check used PyMuPDF, pypdf, Poppler, MuPDF, pikepdf, Tesseract, a vector-path decoder and `strace`. No independent human privacy reviewer or institutional release approval has been obtained. The source may be reviewed as an experiment; the output is not a confidential-data release artifact.

## Decision and next work

- **Functional local prototype: GO within the synthetic-only grammar.** It edits text streams, preserves measured structure, publishes atomically and refuses unsupported inputs.
- **Format fidelity: GO only for the measured seven-alias Base14 text fixtures.** Individual glyph boxes still drift and complex real PDF features are unsupported.
- **Auditor equivalence: GO only for the 13 exercised rule IDs on these generated fixtures.** A per-rule compatibility contract and adjudicated cases are still needed.
- **Technical privacy: REVISE.** Planted literal tokens were removed or sources refused, but word-length/layout leakage and unexamined PDF behavior remain.
- **Real confidential dissertations and sharing output: NO-GO.** Require authorization for any private local evaluation, independent adversarial/re-identification review and a decision on whether the complete local auditor removes the need for transformed PDFs.

No merge, deployment, distribution, reviewer contact, shared-ledger change or other-worktree modification is part of this branch.
