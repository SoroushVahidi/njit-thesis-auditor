# Synthetic PDF text replacement experiment — October 15, 2026

**Scope:** An offline proof of concept, not a production feature or a safe way to share a confidential dissertation. It does not use encryption. No real or embargoed dissertation was used.

## Method

`experimental_pdf_text.py` accepts only a PDF whose title starts with `SYNTHETIC `. It measures each character's position and font, then creates a **new PDF** and draws an unrelated, nearly equal-width character at the same origin. Digits become different digits. Whitespace and punctuation remain so line gaps and TOC leaders survive. The source PDF's pages, metadata, attachments, and content streams are never copied. A new destination is required.

The experiment rejects rotated or cropped pages; images, drawings and form objects; links, annotations, attachments and forms; non-horizontal or non-ASCII text; nonstandard fonts; and sources over 12 pages, 30,000 characters or 5 MB. The `SYNTHETIC` marker prevents accidental use on ordinary documents; it is not an authenticity or security check.

Run it only on synthetic data:

```bash
python -m scripts.generate_synthetic_obfuscation_fixtures /tmp/njit-poc
PYTHONPATH=src python -m njit_auditor.experimental_pdf_text \
  /tmp/njit-poc/synthetic_helvetica.pdf /tmp/njit-poc/replaced.pdf
PYTHONPATH=src python -m scripts.evaluate_synthetic_obfuscation \
  /tmp/njit-poc-evaluation --trials 5 --output /tmp/njit-poc-evaluation.json
```

## Layout comparison

Three generated text-only PDFs exercise Helvetica, Times and Courier; bold and italic text; portrait and landscape page sizes; paragraph indents; a known left-margin violation; page numbers; headings; a TOC; and a List of Figures. Five independent substitutions were compared for each source (15 transformed PDFs). All measurements below are from synthetic files.

| Source | Pages | Lines | Text blocks | Characters | Largest character-box change | Font name and size |
|---|---:|---:|---:|---:|---:|---|
| Helvetica | 3 | 14 | 13 | 384 | 0 pt | 384/384 names; 0 pt size change |
| Times | 2 | 11 | 10 | 295 | 0.196 pt | 295/295 names; 0 pt size change |
| Courier landscape | 2 | 10 | 9 | 250 | 0 pt | 250/250 names; 0 pt size change |

Page dimensions, line counts, block counts and character counts matched in every trial. Line bounding boxes, including their starts and vertical spacing, had 0 pt maximum change. The Times exception is one glyph-width class without an exact unrelated substitute; its right edge moved by 0.196 pt. Glyph shapes are necessarily different even though the reported font names and sizes match. This result does not cover embedded fonts, diagrams, equations, scans, rotated text, or complex production PDFs.

## Auditor comparison

Signatures match **severity, rule, physical page, issue type and bounding box rounded to 1 pt**. Counts below include WARNING/FAIL findings, not PASS records. The three sources have 38 warnings per trial; repeated across five substitutions, **37/190 matched, 153/190 were lost, and 24 new warnings appeared**. Random replacement produces some variation even with identical geometry. PASS results also changed: the Times and Courier sources each lost their one PASS record.

| Rule | Source × 5 | Matched | Lost | Introduced | Interpretation on these fixtures |
|---|---:|---:|---:|---:|---|
| P011 margins | 5 | 5 | 0 | 18 | The deliberately misplaced Helvetica line stays detected, but obfuscated folios create new bottom-margin warnings. |
| P013 | 50 | 32 | 18 | 0 | Some geometry warnings persist; text-dependent cases disappear. |
| P014 | 15 | 0 | 15 | 0 | No source warnings survive. |
| P017 | 10 | 0 | 10 | 0 | No source warnings survive. |
| P019 page numbering | 10 | 0 | 10 | 1 | Replacing numeric/roman values destroys numbering evidence. |
| P022 | 5 | 0 | 5 | 0 | No source warnings survive. |
| P025 | 10 | 0 | 10 | 0 | No source warnings survive. |
| P026 font | 0 | 0 | 0 | 5 | A warning appears despite matching font names and sizes because classification depends on text context. |
| P031 | 10 | 0 | 10 | 0 | No source warnings survive. |
| P038 front matter headings | 50 | 0 | 50 | 0 | Required headings are no longer recognizable. |
| P040 | 10 | 0 | 10 | 0 | TOC/List structure is no longer recognized reliably. |
| P063 | 5 | 0 | 5 | 0 | No source warnings survive. |
| P085 | 10 | 0 | 10 | 0 | No source warnings survive. |

These are **fixture findings**, not adjudicated results on real dissertations. The intended Helvetica left-margin violation is the only hand-verified true formatting defect in this set; it survives. The observed false positives and lost detections show that geometry alone is insufficient. The other project rule IDs were not exercised and must not be called compatible. Many checks identify sections, captions, page numbers, TOC/LOF entries, abstracts, references, or headings by their actual text or number sequence; changing those tokens can make a check inapplicable or wrong even when every box stays fixed.

## Content-removal checks and limits

Across all 15 outputs, PyMuPDF and pypdf found **zero original source words of five or more letters** in extracted page text. An inspection of output PDF objects and decompressed streams found **zero intact original source lines**. Source titles were absent from output metadata and raw bytes; output authors were blank. The fresh PDFs contained no attachments, images, annotations or links. The tests additionally check a distinctive synthetic token and reject unsupported features without leaving an output file.

These checks do **not** establish confidentiality. Word lengths, punctuation, line breaks, font identities, exact character positions and nearly exact glyph-width sequences remain. That geometry can fingerprint or narrow candidate text, especially if an attacker has outside knowledge. Random glyph replacement is not cryptographic encryption, and residual patterns or PDF viewer behavior have not been assessed against a motivated adversary. Images that contain text, uncommon fonts, attachments and other complex features are rejected rather than transformed. The `SYNTHETIC` title is user-editable and cannot verify that a file is nonconfidential.

## Decision

**Requires redesign.** The geometry reconstruction is useful as an engineering demonstration with synthetic documents, but the resulting PDF is not a reliable substitute for the original in the full auditor and is not approved for confidential sharing. Do not present it to Dr. Ziavras as a ready privacy solution. A future approach would need an explicit per-rule compatibility contract, preservation of approved structural tokens without exposing research content, a much broader PDF feature model, adversarial privacy testing, and institutional data-handling approval. This experiment is not merged or deployed.
