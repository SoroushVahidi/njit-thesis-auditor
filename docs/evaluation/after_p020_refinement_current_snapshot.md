# Current Auditor Snapshot After P020 Refinement

## Purpose

Short post-PR refresh evaluating the effect of PR #37 (CMBX/font-size heading detection
refinement) on all available dissertation data. Because the change updates font-style
extraction at the PDF layout layer, it may affect any bold/italic-aware rule (P014, P020,
P027). This snapshot confirms the impact is scoped and conservative.

## Auditor Version

- **Main commit:** `96543ef` — "Refine P020 heading detection (#37)"
- **P001–P028** implemented; P020 now includes CMBX bold recognition and font-size fallback
- **Prior snapshot:** `docs/evaluation/current_auditor_after_p028_evaluation.md` (commit `4bf5a22`)

---

## Finding Counts (Bold/Italic-Aware Rules)

Δ columns show difference vs. the prior P001–P028 evaluation snapshot.

| File | Total | P014 | P020 | P027 | ΔP014 | ΔP020 | ΔP027 |
|------|------:|-----:|-----:|-----:|------:|------:|------:|
| Cibaku Elson (1st) | 322 | 1 | **2** | 1 | 0 | **+2** | 0 |
| Yin H 2nd (260415) | 285 | 1 | **1** | 0 | 0 | **+1** | 0 |
| Yin Haotian 2nd | 350 | 1 | **1** | 0 | 0 | **+1** | 0 |
| Yin H 4th (compressed) | 555 | 10 | 30 | 2 | 0 | 0 | 0 |
| Sebastian Fine (baseline) | 60 | 6 | 3 | 0 | 0 | 0 | 0 |

### P020 Detection Reason Breakdown

| File | cmbx_bold_heading | bold_heading | font_size_heading_fallback |
|------|:-----------------:|:------------:|:--------------------------:|
| Cibaku Elson (1st) | **2** | — | — |
| Yin H 2nd (260415) | **1** | — | — |
| Yin Haotian 2nd | **1** | — | — |
| Yin H 4th (compressed) | — | 30 | — |
| Sebastian Fine (baseline) | — | 3 | — |

---

## Analysis

### P020 Changes

**CMR-based PDFs (Cibaku Elson, Yin H 2nd):** P020 went from 0 to 1–2 findings.
All new findings use `cmbx_bold_heading`, confirming they were triggered by the CMBX
recognition fix rather than the font-size fallback. These are section headings typeset
in CMBX12 (Computer Modern Bold Extended) that have title-case violations.

**Yin H 4th (compressed):** No change. This PDF uses Georgia/Arial with explicit bold
metadata — already detected before the refinement.

**Sebastian Fine (baseline):** No change — stays at 3. The baseline does not use CMBX
fonts for headings, so the CMBX fix does not inflate its findings.

**Font-size fallback:** Not triggered on any evaluated PDF. This is expected:
- CMR/CMBX PDFs use 12pt headings (same size as body) — no size difference to detect
- Yin 4th uses explicit bold metadata already

The fallback is ready for document types where headings are noticeably larger than body
(e.g., Word documents with 14pt headings), but none of the current test files exercise it.

### P014 Changes

No change across any file. The CMBX recognition update affects `span.bold` at
extraction time, which P014 also reads. However, P014 already had its own
`BOLD_FONT_HINT_RE` pattern in `pdf_headings.py`, which effectively covered CMBX
via the in-place font-name check. The net effect on P014 is zero.

### P027 Changes

No change across any file. P027 uses numbered section patterns (1.1, 1.1.1) for level
inference — it does not rely on bold detection as a primary trigger.

---

## Conclusion

The P020 CMBX refinement:
- **Improved recall** on CMR-based PDFs (Cibaku +2, Yin 2nd +1) with no false-positive
  increase on the clean baseline.
- **Scoped impact:** only P020 changed; P014 and P027 are unaffected.
- **Conservative:** new findings are real CMBX heading title-case violations, not noise.
- **Font-size fallback:** not yet exercised by current test data; will activate for
  documents with larger headings.

---

## Recommended Next Implementation Bundles

### Bundle A: Roman Numeral Sequence Ordering (P029)
**Rationale:** P028 checks that front-matter pages use Roman numerals (not Arabic), but does
not validate the sequence order (i, ii, iii, iv...). Cibaku's 8 Arabic-on-front-matter
findings are real violations; after fixing the regime style, the next step is sequence
correctness.  
**Q-rule basis:** Q022, Q031, Q035, Q046, Q060  
**Risk:** Medium

### Bundle B: P011 Compression Artifact Guard
**Rationale:** Yin H 4th (compressed) still shows 150 P011 findings vs 14–33 on normal PDFs.
A per-page compression detection heuristic or adaptive threshold would reduce this noise.  
**Modules:** `pdf_margins.py`  
**Risk:** Medium

### Bundle C: P014 Named Heading Bold Metadata Enhancement
**Rationale:** Sebastian Fine baseline shows 6 P014 warnings on a clean PDF. These are
likely caused by headings without accessible bold metadata. After the CMBX fix, if CMBX
headings on this file are now correctly recognized as bold, these warnings may resolve;
otherwise investigate further.  
**Risk:** Low — investigation and minor calibration only
