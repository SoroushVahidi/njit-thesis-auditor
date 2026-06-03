# Reusable Thesis Formatting Tooling Audit

- **Date:** 2026-06-02
- **Branch:** docs/reusable-tooling-audit
- **Baseline main:** `b4b6594` (P001–P036 implemented; P037 scoped)
- **Purpose:** Evaluate whether existing open-source tools can accelerate this project before continuing rule-by-rule implementation

---

## 1. Executive Summary

Four candidate tools and two layout-analysis ecosystems were inspected. **None is suitable for direct dependency.** The closest candidate, `AndrewGreenbaum/thesis-compliance`, shares our PDF stack (pdfplumber + PyMuPDF) and implements YAML-driven university specs with rule overlap across margins, fonts, spacing, page numbering, headings, captions, and bibliography. However, it has 5 commits, 0 stars, and shows signs of being an AI-scaffolded prototype — it carries no community track record and would be a reliability liability if vendored. The remaining tools are either plain-text-only, research-grade ML tools requiring GPU, or stale.

**Key conclusions:**
- No tool should be added as a direct or optional dependency.
- The YAML-driven university spec concept from `thesis-compliance` is worth borrowing as a future configuration layer once our rule set stabilizes.
- Deep-learning layout tools (deepdoctection, LayoutParser) are worth tracking for a future P035 v2 that handles image-only floats, but are too heavy for v1.
- **P037 should proceed immediately.** No integration spike is warranted.

---

## 2. Tool Comparison Table

| Tool | Checks Rendered PDF | Domain | License | Maturity | Tests | GPU Needed | Integration Verdict |
|------|:-------------------:|--------|---------|:--------:|:-----:|:----------:|---------------------|
| AndrewGreenbaum/thesis-compliance | Yes (PyMuPDF) | Thesis formatting | MIT | Very early (5 commits, 0 stars) | Yes (synthetic) | No | Reference/inspiration only |
| norx1991/Dissertation-Format-Checker | No (plain text) | Ref/figure cross-ref | None | Minimal | No | No | Not useful |
| lamps-lab/ETDMiner | Partial (OCR, ML classifier) | ETD metadata/mining | MIT | Research-grade (269 commits, 7 stars) | No | Recommended | Not useful now |
| LayoutParser + PubLayNet | Yes (Detectron2 regions) | General documents | Apache-2.0 | Stale (last release Apr 2022) | Yes | Practically required | Not useful now |
| deepdoctection + DocLayNet | Yes (Detectron2 regions) | General documents | Apache-2.0 | Active (v1.2.11, May 2026) | Yes | Recommended | Not useful now |

---

## 3. Detailed Tool Notes

### 3.1 AndrewGreenbaum/thesis-compliance

**License:** MIT  
**Language/dependencies:** Python ≥ 3.11; `pymupdf ≥ 1.23`, `pdfplumber ≥ 0.10`, `typer[all]`, `rich`, `pydantic ≥ 2`, `PyYAML ≥ 6`. Optional: `fastapi`, `uvicorn` for REST API. Dev: `pytest`, `ruff`, `mypy` — identical stack to ours.

**Architecture:** YAML-driven university specs (`--spec university.yaml` or custom file). Eight built-in specs: `rackham.yaml` (UMich/default), `unc.yaml`, `rice.yaml`, `stanford.yaml`, `mit.yaml`, `cornell.yaml`, `harvard.yaml`, `chicago.yaml`. Each YAML encodes margin values with tolerance, allowed font names and body size, line-spacing ratio with tolerance, page-numbering style and alignment. Checks are organized in an `extractor/` package with separate modules per concern and a `checker/` engine with `evaluators.py`, `violations.py`.

**Rendered PDF or source?** Rendered PDF only. PyMuPDF is the primary extraction engine for glyph-level properties; pdfplumber appears for coordinate mining.

**What it checks (23 rules):**
- Margins: 1.5" left binding, 1" others
- Fonts: 12pt Times/Arial body enforcement
- Spacing: double-spacing
- Pages: page-level properties
- Headings: size, boldness, capitalization
- Captions: font size, labeling, sequence numbering
- Bibliography: hanging indents, font size, entry spacing
- Title page: 2" top margin
- Page numbering: Roman front matter, Arabic body

**Tests:** 15 test modules (`test_margins.py`, `test_fonts.py`, `test_spacing.py`, etc.) using programmatically generated synthetic PDFs (`tests/fixtures/generate_pdfs.py`). No real student documents required.

**Maturity concern:** 5 commits total, 0 stars, 0 forks. A `claude.md` file in the root strongly implies it was scaffolded by an AI coding assistant. It has no community track record, no issue history, no CI configuration. The architecture is coherent and the spec system is well-designed, but the implementation has not been validated against a real university's dissertation corpus. Should be treated as a reference prototype, not a production-proven tool.

---

### 3.2 norx1991/Dissertation-Format-Checker

**License:** None specified.  
**Language:** Python. No documented external dependencies.

**What it checks:** Operates on plain text files only (`dissertation.txt` body + `ref.txt` reference list). Five consistency checks: (1) references not cited in text, (2) references cited but missing from list, (3) figure files not mentioned, (4) figures mentioned without entry, (5) figure mention sequence vs. list order.

No PDF parsing, no layout analysis, no formatting compliance. Not relevant to this project.

---

### 3.3 lamps-lab/ETDMiner

**License:** MIT.  
**Languages:** HTML 89%, Jupyter Notebook 8%, Python 3%.  
**Stars:** 7. **Commits:** 269. **Affiliation:** LAMPS Lab research group.

**What it does:** Text mining toolkit for Electronic Theses and Dissertations at scale. Modules: (a) `AutoMeta`/`etd_crf` — CRF-based metadata extraction from scanned cover pages (title, author, advisor, degree, year); (b) `etd_segmentation` (ETDPC) — multimodal ML page classifier (research baseline, ablation, and "ours" model); (c) metadata correction, HTML parser, web crawler.

**Page classification:** ML-based research classifier; not a rule-based compliance checker. Requires trained models. OCR via Tesseract + Pillow + OpenCV for scanned ETDs.

**For this project:** The page classification approach is conceptually related to `_classify_pages()` in our `pdf_page_numbering_regime.py`, but our heuristic version already covers front-matter/body detection without ML. Adding ETDMiner would require GPU, trained model artifacts, and a non-trivial integration layer for marginal gain.

---

### 3.4 Layout Analysis Tools (PubLayNet / DocLayNet / deepdoctection)

**LayoutParser + PubLayNet (Apache-2.0):** Detectron2-based region detector (Text, Title, List, Table, Figure). Last release April 2022 — effectively unmaintained. 98 open issues. GPU practically required (~1,700ms/page CPU vs ~67ms GPU). Output is bounding-box regions, not compliance measurements. Not useful now.

**deepdoctection + DocLayNet (Apache-2.0):** Actively maintained (v1.2.11, May 2026). PyTorch ≥ 2.6, transformers ≥ 4.48, Detectron2 (not on PyPI), pdfplumber ≥ 0.11. More granular (11 label classes). Heavy dependency chain. No thesis-domain training data — would require fine-tuning. GPU recommended. Output is region bounding boxes, not margin widths or font names.

**Future potential (P035 v2):** If we need to detect image-only figure/table bodies (skipped in P035 v1), a region detector could identify figure/table regions on pages where the text layer has no body content. deepdoctection is the most plausible candidate — it is active, uses pdfplumber which we already use, and has document-native PDF input. But this is a future concern, not a v1 priority.

---

## 4. Overlap Matrix: thesis-compliance vs Our Rules

Rules where `thesis-compliance` implements an equivalent check:

| Our Rule | thesis-compliance Equivalent | Notes |
|----------|------------------------------|-------|
| P011 Margins | `extractor/margins.py` | Left 1.5", others 1" — same boundaries; YAML tolerance field |
| P023 Body spacing | `extractor/spacing.py` | Double-spacing ratio with tolerance — equivalent to our 1.55× threshold |
| P026 Font compliance | `extractor/fonts.py` | 12pt Times/Arial; YAML-configurable allowed fonts |
| P027 Heading style | `extractor/headings.py` | Size, boldness, capitalization — partial overlap with our level-specific style |
| P028/P029 Page numbering | page numbering module | Roman front matter, Arabic body — our regime check and sequence check |
| P017 Captions | `extractor/captions.py` | Caption font size, labeling, sequence — partial overlap |
| P014 Headings layout | `extractor/headings.py` | Bold/capitalization checks — partial overlap |

Rules where `thesis-compliance` has **no equivalent** (our advantages):

| Our Rule | Gap in thesis-compliance |
|----------|--------------------------|
| P012 Annotations | Not addressed |
| P013 Page-number candidates (detailed) | Only pass/fail; no candidate-level detail |
| P015 Indentation | Not addressed |
| P016 Spacing (front-matter gaps) | Not addressed |
| P018 TOC alignment | Not addressed |
| P019 Page number consistency | Not addressed |
| P020 Title capitalization | Not addressed |
| P021 Abstract word count | Not addressed |
| P022 No-number page check | Not addressed |
| P024 TOC/List formatting | Not addressed |
| P025 Front-matter structure | Not addressed |
| P030 TOC continued headings | Not addressed |
| P031 LoT/LoF column headers | Not addressed |
| P032 Wrapped entry spacing | Not addressed |
| P033 Title consistency | Not addressed |
| P034 Copyright page | Not addressed |
| P035 Figure/table layout | Not addressed |
| P036 TOC inter-entry spacing | Not addressed |
| P037 Section-anchored Roman numerals | Not addressed |

Rules in `thesis-compliance` with **no current equivalent in ours**:

| thesis-compliance Check | Gap in Our Rules |
|-------------------------|-----------------|
| Bibliography hanging indents, font size, entry spacing | No bibliography checks in P001–P036 |
| Title page 2" top margin (distinct from 1.5" binding margin) | P011 checks text overflow but not the 2" title-page top margin specifically |
| Caption sequence numbering (Figure 1, Figure 2...) | P017 checks punctuation but not sequential numbering integrity |

---

## 5. Integration Recommendation

| Tool | Recommendation | Rationale |
|------|---------------|-----------|
| AndrewGreenbaum/thesis-compliance | **Reference/inspiration only** | MIT license, compatible stack, good YAML spec concept, but 0 stars / 5 commits / AI-scaffolded — too immature to depend on |
| norx1991/Dissertation-Format-Checker | **Not useful** | Plain text only; no PDF layout relevance |
| lamps-lab/ETDMiner | **Not useful now** | Research ML tool; GPU required; our heuristic page classifier already covers the needed functionality |
| LayoutParser + PubLayNet | **Not useful now** | Stale since 2022; GPU required; general domain |
| deepdoctection + DocLayNet | **Track for P035 v2** | Active, pdfplumber overlap, but heavy and no thesis-domain data |

**No external tool should be added as a dependency (direct or optional) at this time.**

---

## 6. Specific Questions Answered

### Can thesis-compliance accelerate our remaining rules?

| Rule Area | thesis-compliance Relevance | Assessment |
|-----------|----------------------------|------------|
| P011 margins | Partial overlap | They check the same NJIT margins. We have compression artifact guard; they don't. Our implementation is more mature for this domain. |
| P013/P019/P028/P029/P037 page numbering | Partial overlap | They check Roman/Arabic regime. We have deeper candidate detection, sequence ordering, and (upcoming) section-anchored checks. |
| P014/P027 headings | Partial overlap | They check bold/caps/size. We have centered-near-top plus text-area center correction for NJIT asymmetric margins — not in thesis-compliance. |
| P017/P035 captions | Partial overlap | They check caption labeling/size/sequence. We check terminal punctuation and body placement geometry. Different angles. |
| P023 body spacing | Near-equivalent | Same concept (double-spacing ratio). Our threshold (1.55×) is tuned for NJIT EF-annotated PDFs; theirs uses YAML tolerance. |
| P026 font compliance | Near-equivalent | Same concept (12pt Times body). Our implementation is already mature. |
| Future bibliography | Relevant | Their `bibliography.py` covers hanging indents, font size, entry spacing — three checks we have no equivalent for. If we add bibliography rules, their approach is worth studying. |
| YAML-driven spec | Conceptual value | The YAML university-spec architecture is the most transferable idea. Worth adopting if/when we need to support multiple universities. |

### Should we borrow the YAML spec idea?

Yes, as a **future enhancement** after P037 and the next implementation bundle. Currently our checks are hardcoded to NJIT values (1.5"/1" margins, Times New Roman 12pt, iv bio-sketch anchor). A YAML spec layer would generalize the auditor to other institutions. This is not needed before P037.

### Should we create an optional external-baseline adapter?

No. thesis-compliance is too immature to be a reliable baseline. The overlap is partial, and our implementations are more NJIT-specific and better-tuned. Maintaining an adapter would add complexity without benefit.

---

## 7. Risks

| Risk | Likelihood | Mitigation |
|------|:----------:|-----------|
| thesis-compliance becomes active and diverges from our approach | Low | Our rules are NJIT-specific; any future port would need NJIT YAML spec authoring, not code dependency |
| deepdoctection dependency chain breaks P035 v2 | Medium | Evaluate only at P035 v2 scope; keep it optional/external |
| Layout analysis tools never reach thesis-domain maturity | Medium | Acceptable — our heuristic PDF approach already handles text-layer bodies for P035 |
| Bibliography rule gap widens | Low | Not in scope for P037; note for future bundle |

---

## 8. Recommended Next Task

**Implement P037 immediately.** No tooling integration spike is warranted.

The section-anchored Roman numeral rule (P037) has clear Q-rule basis (Q022, Q031, Q035, Q046, Q060), a complete scope document (`docs/planning/p037_scope_and_design.md`), synthetic test plan, and reuses existing helpers (`_classify_pages`, `detect_page_number_candidates`, `find_named_frontmatter_headings`). No external tool addresses it.

After P037, consider:
1. Front-matter exact heading phrase / missing-section detection (P014 follow-on, Candidate B from P037 scope doc)
2. Bibliography checks (no external tool to depend on, but thesis-compliance's approach is a useful reference)
3. YAML spec configuration layer (future, after rule set stabilizes)

---

## 9. P037 Decision

**P037 should proceed — do not pause.**

No inspected tool covers section-anchored Roman numeral validation. thesis-compliance's page numbering check is limited to Roman-vs-Arabic regime detection (equivalent to our P028) and does not perform section-anchored anchor validation (P037's scope). ETDMiner's page classifier is ML-based and research-grade. P037 builds directly on our existing P028/P029/P014 stack and is fully scoped.
