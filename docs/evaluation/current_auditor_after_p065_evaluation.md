# Full Auditor Evaluation After P065 — Five-PDF Aggregate Snapshot

**Date:** 2026-06-08  
**Baseline commit:** `b233f3b` (PR #233 — P065 current-dataset evaluation complete)  
**Validation status:** ruff clean, mypy clean, 925 pytest passed  
**Auditor scope:** P001–P065 implemented; PDF layout audit includes P011–P065

---

## Evaluated Files

| File label | Pages | Accessible | Source |
|---|---|---|---|
| Cibaku Elson 1st Review | 99 | Yes | tracked PDF |
| Yin H 2nd Review (flattened) | 108 | Yes | tracked PDF |
| Yin Haotian 2nd Review | 108 | Yes | tracked PDF |
| Yin H 4th Review (compressed) | 137 | Yes | tracked PDF |
| Sebastian Fine clean baseline | 29 | Yes | extracted from tracked ZIP |

Sebastian Fine was extracted from
`data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip`
into `data/evaluation/generated/current_auditor_after_p065/` (gitignored; not
committed).

---

## Findings by File

| Rule | Cibaku | Yin H 2nd flat | Yin Haotian 2nd | Yin H 4th comp | Seb Fine | Total |
|---|---|---|---|---|---|---|
| P011 | 21 | 33 | 33 | 70 | 12 | **169** |
| P012 | 78 | — | 65 | — | — | **143** |
| P013 | 95 | 104 | 104 | 133 | 25 | **461** |
| P015 | 5 | 13 | 13 | 8 | — | **39** |
| P016 | 1 | 2 | 2 | 4 | 2 | **11** |
| P017 | — | — | — | 23 | 1 | **24** |
| P018 | — | — | — | 17 | 2 | **19** |
| P019 | 8 | 15 | 15 | 25 | 4 | **67** |
| P020 | 2 | 1 | 1 | 30 | 3 | **37** |
| P023 | 6 | 4 | 4 | — | 1 | **15** |
| P024 | — | — | — | 12 | — | **12** |
| P026 | 92 | 103 | 103 | 117 | — | **415** |
| P027 | 1 | — | — | 2 | — | **3** |
| P028 | 8 | — | — | 8 | — | **16** |
| P029 | — | — | — | 12 | — | **12** |
| P030 | — | — | — | 3 | — | **3** |
| P035 | — | — | — | 13 | 1 | **14** |
| P036 | — | — | — | 77 | — | **77** |
| P037 | — | — | — | 2 | 1 | **3** |
| P038 | 4 | 4 | 4 | 2 | 2 | **16** |
| P040 | — | — | — | 12 | 1 | **13** |
| P044 | 3 | 1 | 1 | 1 | 1 | **7** |
| P046 | — | — | — | 2 | — | **2** |
| P048 | — | — | — | 1 | — | **1** |
| P049 | — | — | — | 1 | — | **1** |
| P051 | 1 | 1 | 1 | — | — | **3** |
| P053 | — | — | — | 2 | — | **2** |
| P054 | — | — | — | 1 | — | **1** |
| P058 | — | — | — | 1 | — | **1** |
| P065 | — | — | — | — | — | **0** |
| **Total** | **325** | **281** | **346** | **579** | **56** | **1,587** |

Dashes (—) indicate zero findings for that rule/file combination.

---

## Aggregate Findings by Rule

| Rule | Total | Description |
|---|---|---|
| P013 | 461 | Page-number candidates |
| P026 | 415 | Possible body font family issue |
| P011 | 169 | Margin/overflow |
| P012 | 143 | PDF annotations |
| P036 | 77 | TOC/LoT/LoF entry spacing |
| P019 | 67 | Page number format |
| P015 | 39 | Paragraph indentation |
| P020 | 37 | Title/heading capitalization |
| P017 | 24 | Caption terminal punctuation / caption type |
| P016 | 11 | Blank line spacing |
| P023 | 15 | Body spacing |
| P018 | 19 | TOC alignment |
| P028 | 16 | Page numbering regime |
| P038 | 16 | Front-matter heading presence |
| P035 | 14 | Figure/table layout |
| P040 | 13 | LoF terminal punctuation |
| P024 | 12 | TOC list formatting |
| P029 | 12 | Page numbering |
| P027 | 3 | Heading level issues |
| P030 | 3 | TOC continued headings |
| P037 | 3 | Roman numeral section anchors |
| P051 | 3 | Copyright year format |
| P053 | 2 | LoT terminal period |
| P046 | 2 | LoT/LoF entry number alignment |
| P048 | 1 | LoT/LoF page number alignment |
| P049 | 1 | LoT/LoF page-column header alignment |
| P054 | 1 | TOC terminal period |
| P058 | 1 | TOC page number ordering |
| P065 | **0** | Dedication centering/italic |

Rules with zero aggregate findings (not listed above): P014, P022, P025, P032,
P033, P034, P039, P041, P042, P043, P044 (shown as 7 above; see by-file),
P045, P047, P050, P052, P055, P056, P057, P059, P060, P061, P062, P063, P064,
P065.

---

## Aggregate Findings by Category

| Category | Total |
|---|---|
| page_numbering | 559 |
| font_format | 415 |
| margin_or_overflow | 169 |
| annotations | 143 |
| list_of_tables_figures_toc | 132 |
| indentation | 46 |
| table_format | 38 |
| capitalization_case | 37 |
| spacing_blank_lines | 26 |
| heading_title | 19 |
| title_page_metadata | 3 |
| **Total** | **1,587** |

---

## Comparison with P064-Era Snapshot

| Metric | P064-era | Post-P065 | Delta |
|---|---|---|---|
| Grand total | 1,587 | 1,587 | **0** |
| P065 findings | — | 0 | — |

**The aggregate total is unchanged at 1,587.** P065 added 0 findings across
all five evaluation PDFs. This is expected: P065 detected no machine-readable
standalone DEDICATION heading in the first 15 pages of any file, causing all
five files to skip the centering and italic checks. The rule was not
exercised on real data.

Historical baselines for reference:
- P034-era (P011–P034 only): **1,446** findings
- P061/P062/P063/P064-era (P011–P064): **1,587** findings
- Post-P065 (P011–P065): **1,587** findings

---

## P065 Analysis

P065 (`dedication_text_not_centered`, `dedication_text_not_italic`) fired on
**0 of 5 files**. All five PDFs were skipped at the detection gate:

- **Cibaku, Yin H 2nd, Yin Haotian, Yin H 4th:** No text containing
  "DEDICATION" was found in the first 15 pages. Dedication pages, if present,
  are likely image-rendered.
- **Sebastian Fine:** The substring "DEDICATION" appears once within body
  prose (an 82-character line), not as a standalone page heading, so the gate
  correctly did not fire.

**Absence of P065 findings does not prove dedication formatting compliance.**
The current evaluation dataset does not contain machine-readable standalone
DEDICATION headings in the text layer. P065 will exercise its centering and
italic checks only on future PDFs with a DEDICATION heading in the text layer.

See `docs/evaluation/p065_current_dataset_evaluation.md` for the dedicated
P065 gate-by-gate analysis.

---

## Largest Rules and Categories

Top five rules by finding count:
1. P013 — page-number candidates: **461**
2. P026 — font format: **415**
3. P011 — margin/overflow: **169**
4. P012 — annotations: **143**
5. P036 — TOC/LoT/LoF entry spacing: **77**

Top categories:
1. `page_numbering`: **559**
2. `font_format`: **415**
3. `margin_or_overflow`: **169**
4. `annotations`: **143**
5. `list_of_tables_figures_toc`: **132**

---

## File-Level Summary

| File label | Total findings | Main contributors | Notes |
|---|---|---|---|
| Cibaku Elson 1st Review | 325 | P013 (95), P026 (92), P012 (78) | EF annotations inflate P012 |
| Yin H 2nd Review (flattened) | 281 | P013 (104), P026 (103) | Flattened — no live annotations |
| Yin Haotian 2nd Review | 346 | P013 (104), P026 (103), P012 (65) | Extractable EF comments |
| Yin H 4th Review (compressed) | 579 | P013 (133), P026 (117), P036 (77) | Most rules active; compressed text layer |
| Sebastian Fine clean baseline | 56 | P013 (25), P011 (12) | No EF annotations; 29-page draft |

---

## Generated Output Path

```
data/evaluation/generated/current_auditor_after_p065/
```

Contents (gitignored, not committed):
- `sebastian_fine_clean.pdf` — extracted from tracked ZIP for audit
- `aggregate.json` — machine-readable per-file and per-rule counts

The `.gitignore` entry `data/evaluation/generated/` covers this directory.
No generated JSON, Markdown, or extracted PDF files are committed.

---

## Privacy Model

- No dissertation text, dedication content, author names, committee names,
  title text, EF comment text, body prose, DOI strings, or URLs from any
  evaluated file are quoted in this document.
- All reported values are counts, page numbers, and rule/category labels.
- Real dissertation files were not modified.
- No OCR was performed. No external network calls were made.

---

## Limitations

- P065 was not exercised on real data (no machine-readable DEDICATION heading
  in first 15 pages on any file in this dataset).
- Rules with zero aggregate findings on this dataset (P014, P022, P025, P032,
  P033, P034, P039, P041–P043, P045, P047, P050, P052, P055–P057, P059–P065)
  do not indicate compliance — the dataset may not trigger those checks.
- The five-PDF evaluation set is small and not representative of all NJIT
  dissertations; findings patterns reflect the specific review rounds and
  submission states of these particular documents.
- Yin H 2nd Review (flattened) lacks a live text layer for some pages;
  findings reflect what PyMuPDF can extract.
