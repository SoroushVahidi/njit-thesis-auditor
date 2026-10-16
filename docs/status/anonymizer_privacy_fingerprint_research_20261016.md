# Synthetic PDF anonymizer: privacy and fingerprint research (2026-10-16)

**Decision:** the prototype remains a local **synthetic-only research tool**. Do not use it on confidential dissertations or share its transformed PDFs as anonymous documents. This study demonstrates that preserving line geometry lets an attacker with candidate original PDFs identify the source, even when literal source words and their length pattern are changed.

## Starting point and verified baseline

This work started from PR #623 head `b63920f2675eca09098069f16af04d64a0031851`, on the isolated branch `audit/anonymizer-privacy-20261016`. PR #623 was open and draft at that SHA. Its CI jobs reported failure with no runner or executed steps; they are **not** passing validation. The prior local full-suite log and exit file show `4,801 passed, 10 skipped, 3 warnings` and exit 0 on that starting source. The final-source validation is reported below separately.

A fresh five-trial replay on the exact starting commit reproduced 190/190 strict historical auditor findings and 221/221 across six synthetic fixture families, with zero lost or new findings for the balanced method. The structural editor matched 205/221; the October 15 redraw matched 43/202 and refused one extended case. These values are generated-fixture measurements, not detector accuracy against real dissertations. The strict comparison uses a multiset of rule, issue type, page, severity, and rounded bounding box, including multiplicity; it does not align findings by row order.

The replay covered 18 source/output pairs, 43 pages, 208 blocks, 225 lines, and 5,906 characters. Page boxes, all line starts/baselines, 225 font/size signatures, and span counts matched. Maximum line-right drift was **0.031982 pt**; maximum per-character box drift was **3.520019 pt**. Six masked render comparisons found zero changed pixels outside text regions. All 18 outputs retained exact source word-length sequences. A separate generated hostile set refused 21/23 inputs without output; the two accepted files were supported text-only forms. Four artificial planted tokens had zero recoveries across PyMuPDF, pypdf, Poppler, MuPDF, decoded objects, raw bytes, and metadata. This does not establish removal of arbitrary unknown encodings or content.

| Generated baseline source | SHA256 |
|---|---|
| Helvetica | `162667c9b54d1a5dfda2fed377a2b8ea31692176e6ed9ca4fb75a9b17bb51c3b` |
| Times | `e3661681dde37165f657e83f89d0e27e65b4df3df35dd6baff9c7f3748ef5a8c` |
| Courier landscape | `cdab599a247f9fd75c68e0af9dae2d53c17e08d44d406c6859590f0c216f3de5` |
| Extended text-only | `dd02ddc48498b3dc6567bc27a8579d98caa96573063172373baa0b2b1a31c9f0` |
| List of tables | `f1d666700ca7bb1dfb767d7494f6e010120b1b6a2ccad9173194e01b6c032c7d` |
| Text-only multi-column | `cb9e1c14dca2ac74eed20363ebefbc6698028db155ff544ff93d4d3b5720f6ec` |

Historical-family seeds were 1–5; supplemental-family seed was 1. Raw PDFs and per-pair JSON are private and uncommitted.

## Reused editor and limits

The implementation continues to use separately installed `pdf-edit-engine` v0.2.0 at `cee1d2cc042f84d0fb02c874765509c04a8624ac` for Tj/TJ editing in existing text streams. Its installed `direct_url.json` confirms that revision. Its surgeon and width utilities already handle font encoding, glyph widths, and advance compensation, so this branch adds only replacement policy and gate logic. The project's existing adapter uses PyMuPDF's `get_text_length` for Base14 width planning, pikepdf for a fresh full rewrite, and multiple extractors for post-edit checks. No PDF engine source was vendored.

The earlier reuse study also inspected Atelier PDF at `ecece75faacaec08aa00b402351358963f07c9ef` (Tj/TJ editing and width/fit utilities), pikepdf 10.17.0, PyMuPDF 1.28.2, and experimental de-identification tools. Atelier directly retained planted metadata/object tokens without the local safety wrapper; no editor alone is a sanitizer. Installed licenses were checked: pdf-edit-engine and Atelier PDF are MIT (retain notices on redistribution), pikepdf is MPL-2.0 with wheel third-party notices, and PyMuPDF/MuPDF is AGPL-3.0 or commercial. No distribution or deployment is authorized or performed.

## Attack design

The committed benchmark generates **120 source PDFs locally**, using four Base14 font/page/layout templates, three synthetic vocabulary distributions, one- and two-page cases, and fixed line placement within each template. It never embeds a document ID in page text or metadata. The development set has 80 documents; the held-out set has 40, ten per template. The split and attack scores are fixed before strategy evaluation. The filename index is used only for scoring after ranking. The editable `SYNTHETIC` title is not provenance proof; the controlled generator, recorded seeds, and per-source SHA256 hashes in private `linkage-final3/results.json` provide reproducible local provenance, with the normal limitation that local files and the generator can be modified.

The attacker knows candidate **original PDFs** and compares each output to candidates of the same template, which removes easy page-size and font discrimination. Candidate sets contain 2, 5, or 10 held-out originals; development also uses 20. The page-count/dimension attack, layout/font/heading-position attack, line-width geometry attack, word-length-sequence attack, and combined attack were fixed in code. The geometry-only path never accesses the extracted replacement string or its word-length feature. Ties receive fractional credit, so file ordering cannot inflate top-1. The four templates contain no unique placement per document; differences in line widths arise from shared-vocabulary synthetic content. Results therefore measure the candidate-original threat on this population, not a population-wide anonymity probability.

## Strategies and measured separation

- **Balanced:** existing width-balanced glyph replacement, with original word boundaries retained.
- **Boundary:** moves eligible breaks in nonstructural lines and compensates total line width; rule-bearing prefixes, headings, entries, and folios remain under the existing conservative marker policy.
- **Segmented:** samples a new break pattern independent of original word lengths in nonstructural lines, then selects among fixed-seed attempts by line-width error. The same structural marker policy and full gates apply. It does not use held-out labels to choose replacements.

| Strategy | Accepted / 120 | Strict auditor matched | Exact word pattern | Mean aligned length correlation | Max right drift | Max glyph-box drift | Held-out geometry-only top-1, 10 candidates | Word-only top-1, 10 candidates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Balanced | 120 | 441/441 | 100% | 1.0000 | 0.000092 pt | 4.656 pt | **40/40 (100%)** | 100% |
| Boundary | 117 | 426/426 | 0% | 0.6647 | 0.043915 pt | 6.000 pt | **38/38 (100%)** | 98.25% |
| Segmented | 116 | 429/429 | 0% | 0.1041 | 0.230988 pt | 6.684 pt | **36/36 (100%)** | 55.56% |

All accepted outputs had zero new or lost strict findings, zero recovered nonstructural source words in the tested independent extractors, and zero detected residual structures. The boundary strategy refused three inputs; segmented refused four, all because the layout/auditor gate failed. Refusal leaves no output. The accepted-only attack rates must not conceal those refusals. The maximum segmented line-right drift is 0.039% of the narrower 595 pt page width. Individual glyph boxes differ far more than line boxes, so character-level fidelity is not established.

An additional planted-token run recovered none of four artificial tokens from accepted balanced and boundary outputs at seed 29, nor from an accepted segmented output at seed 4. The segmented planted case refused seeds 1–3 before accepting seed 4; those refusals are reported, not treated as passes. This check tests known artificial strings, not all possible original content.

The benchmark's emitted auditor coverage was narrow: **P013** matched 300/300, 291/291, 289/289 and **P026** matched 141/141, 135/135, 140/140 for balanced, boundary, and segmented respectively. A separate strict multiset review by rule, issue type, page, rounded bbox, and multiplicity found zero lost/new issue locations for each strategy. Matching those boxes also preserves the tested finding-highlight locations. The six-family baseline exercised 13 rule IDs; neither set establishes all-rule or semantic equivalence on new wording.

| Held-out same-template candidates | Chance top-1 / top-3 | Page/layout top-1 | Geometry top-1, all strategies | Segmented word-only top-1 / top-3 |
|---:|---:|---:|---:|---:|
| 2 | 50% / 100% | 50% | 100% | 80.56% / 100% |
| 5 | 20% / 60% | 20% | 100% | 66.67% / 86.57% |
| 10 | 10% / 30% | 10% | 100% | 55.56% / 73.15% |

Development geometry-only top-1 was also 100% at 20 candidates, versus 5% chance. Every accepted held-out output had a distinct measured line-width signature. The combined attack matched geometry-only at 100%. A separate Poppler bounding-box parser, using only line coordinates from its output, independently linked 40/40 balanced, 38/38 boundary, and 36/36 segmented outputs uniquely to their ten same-template candidate originals. This is a parser cross-check, **not** an independent human methodology review.

To test whether the benchmark merely rewarded arbitrary source IDs, a separate 20-document **geometry-collision control** held Courier page size, font, line starts, and every line's character count/width fixed while changing synthetic letters and break positions. All three strategies accepted 20/20, with 60/60 strict findings each. Geometry-only top-1 was **5%**, exactly the 1-in-20 chance rate, because all outputs shared one geometry signature. Thus the 100% result above is conditional on distinguishable original line widths; it is those preserved source-specific widths, after template matching, that drive the link. The control's generated PDF hashes, seeds, and script are private in `collision-control/control.json` and `collision_control.py`.

A second review matched lines by page, baseline, left edge, font, size, color, and flags rather than output row order. Across the three strategies it found zero page-box or line-style/anchor mismatches in 120/117/116 accepted pairs and 1,260/1,218/1,211 lines. Twelve representative 72-dpi renders changed inside text masks and had zero changed pixels outside them. Paragraph starts, heading placement, indentation, spacing, and page geometry are represented by those stable anchors and the strict auditor multisets. Semantic equivalence beyond emitted findings and complete glyph-shape equivalence are not proved.

## Upstream degradation and safety gate

The adapter now inspects the **entire** `fidelity_report.degradations` list after every upstream edit. Every emitted event is rejected in this narrow grammar; there is no unreviewed info-level allowance. It also rejects unsuccessful edits, font substitution, overflow, reflow, or missing glyphs. Directly doubling a line in a generated fixture made pinned upstream emit `kerning_compressed` and `overflow_shift_clamped`, both material geometry warnings. Tests inject informational `kerning_widened`, warning `overflow_shift_suppressed`, and error `font_extension_failed` events into otherwise real synthetic edits and confirm atomic refusal with no output. The observed accepted edits emitted no degradation events. An empty upstream list is not treated as fidelity proof: the independent PyMuPDF geometry checks, rendered comparison, auditor multiset, extractor scans, and object-graph checks remain.

The accepted grammar remains limited to small, unencrypted, ASCII, Base14 text-only PDFs with fully accounted-for Tj/TJ shows and a conservative object graph. Embedded/subset fonts, unsupported Unicode, images/scans, vector graphics, Form XObjects, annotations, attachments, hidden layers, forms, XMP, incremental histories, and unexplained objects/operators are refused. The `SYNTHETIC` title is user-editable and cannot authorize real-document processing. The CLI writes a new file only after all checks pass; failed gates leave no published output. No source PDF is overwritten, and no private document or raw LaTeX was processed or uploaded.

## Reproduction and validation

From the branch root, using Python 3.12 and the separately installed pinned editor:

```sh
RUN=/home/soroush/njit-thesis-auditor/.anonymizer-privacy-runs/20261016
python -m scripts.evaluate_anonymizer_prototype "$RUN/baseline" --trials 5 --output "$RUN/baseline.json"
python -m scripts.benchmark_anonymizer_linkage "$RUN/linkage-final3" --seed 20261016 --per-template 30
python -m pytest tests/test_experimental_pdf_anonymizer.py tests/test_benchmark_anonymizer_linkage.py
ruff check .
mypy src
python -m pytest
```

Run the generators in a **new empty private directory** when repeating them: output creation is intentionally non-overwriting. The exact generation seeds and SHA256 manifest are private in `linkage-final3/results.json`. Private `EXPERIMENT_RESULTS.md`, `ATTACK_RESULTS.md`, `adversarial_recheck.json`, `cross_parser_geometry.json`, and `stable_geometry_review.json` contain fuller aggregate evidence. The baseline evaluator's first direct-script attempt failed because it was not invoked as a module; the module command above exited 0. The final-source validation result is recorded below; PR #623's failed-to-start CI jobs remain separate.

Final-source validation used a fresh private Python 3.12 environment. `python -m pip install -e '.[dev]'` and the pinned editor installation succeeded; focused anonymizer and benchmark tests passed (14/14); `ruff check .` and `mypy src` passed. The full `python -m pytest` run exited 0 with **4,808 passed, 10 skipped, 3 warnings in 193.32 seconds**. The skips and warnings remain recorded in the private validation log. A supplementary attempt to type-check the two legacy experiment scripts plus the new benchmark reported 35 errors in the legacy pypdf object-graph/socket typing paths; the new benchmark file passed separately. Those script errors are recorded in the private log and are not presented as a passing gate.

## Verdict and next steps

| Question | Verdict | Scope of evidence |
|---|---|---|
| FUNCTIONAL_PROTOTYPE | PASS | Local synthetic Base14 grammar; unsupported inputs refuse. |
| LAYOUT_FIDELITY | PASS | Accepted synthetic page/line/font/style anchors and sampled renders; individual glyph boxes move. |
| AUDITOR_EQUIVALENCE | PASS | Emitted strict finding multisets on these fixtures only; not all rules or real theses. |
| ORIGINAL_CONTENT_REMOVAL | PASS | Bounded artificial-token and source-word/object scans on accepted synthetic outputs only. |
| STRUCTURAL_UNLINKABILITY | FAIL | Candidate-original geometry-only top-1 100% on held-out accepted outputs. |
| CONFIDENTIAL_DOCUMENT_READINESS | FAIL | Linkability, unproved provenance, narrow grammar, no real-document authorization. |

Preserving individual source line widths and positions exposes a stable fingerprint. If the candidate originals have distinct geometry, a policy confined to changing replacement text cannot guarantee unlinkability while preserving those measurements. It may be possible to tolerate limited formatting differences and reassess auditor compatibility, but that is a different requirement and needs a new study. Safer present options are fully synthetic evaluation documents, offline auditing of originals without sharing transformed PDFs, or continuing synthetic-only research. **Do not share current outputs as anonymous documents.** No independent external reviewer was available; an external privacy/methodology review remains necessary before any confidential-use decision.
