# Ester Source-of-Truth Consistency Audit (Current)

> **Purpose:** Rule-by-rule comparison of the **current** auditor (post–PR #467, `main` @
> `668aa1b`) against Ester Flaim's shared files, transcribed specs, and extracted comment
> examples — **before** any further detector, threshold, or UI changes.
>
> **Recorded:** 2026-07-05 (audit-only pass; live deployment untouched).
>
> **Prior audits (historical):** [ester_current_consistency_audit.md](ester_current_consistency_audit.md) ·
> [ester_language_alignment_audit.md](ester_language_alignment_audit.md) ·
> [ester_current_wording_inventory.md](ester_current_wording_inventory.md) ·
> [ester_feedback_source_of_truth.md](ester_feedback_source_of_truth.md)

**Inspection base:** `origin/main` @ `668aa1bf265ca4fdff74c4ddd59e0b145d9c2300` (includes PR
[#467](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/467) P011 presentation slice +
docs touch-up #468).

**This pass does not change detectors, thresholds, rule IDs, UI behavior, or exports.**

---

## Executive summary

| Dimension | Overall assessment |
|---|---|
| **Criteria (what we warn about)** | Strong coverage of Ester's YES/NO matrix front matter and TOC/List atomics; gaps remain for semantic approval-page ordering (Q015–Q020), references citation-style consistency, and non-text figure/table geometry. Several rules are **broader or noisier** than Ester's practical review (especially P013 page-number *candidates* and P019 umbrella checks). |
| **Language (how we say it)** | Slices 1–6 (PRs #414–#420) brought 29 rules close to Ester's binary question + single-remediation style. PR #467 improved P011 context labels but **diverged** from Ester's sheet remediation (inch settings → context-specific layout fixes). Broad rules (P014, P018, P019, P020, P024, P025) still surface umbrella catalog questions on some paths. |
| **Strictness** | P011 is **strict by design** (Ester-aligned) but mechanically flags sub-4pt text overflows with low confidence; Ester's annotated comments emphasize *visible* margin problems, not point-level measurement. P021/P026 have **documented policy conflicts** with the transcribed sheet. P013 is often **stricter/noisier** than Ester's student-facing practice on EF-annotated PDFs. |
| **Evidence / highlights** | P011 highlight geometry (adjacent groups + margin-boundary guide) is stronger than the 2026-06 WIP branch. Text-layer-only limits remain: table/figure *images*, committee honorifics, and list column regions are only partially highlighted. |
| **UI / report flow** | Current flow (summary → review order → by topic → page order → downloads → advanced) supports Esther-like triage; confidence badges and page-order sort match her “check page by page” workflow. Broad-rule cards can still bundle multiple matrix rows until presentation splits land. |

**Top 5 inconsistencies to resolve with Ester or narrow implementation slices:**

1. **P021 abstract word limits** — detector 150/350 vs transcribed sheet 200/400.
2. **P013 / page-numbering volume** — candidate-based warnings vs Ester's per-page binary checks (Q001, Q008, …).
3. **Broad umbrella rules** — P014/P018/P019/P020 still one catalog question for many matrix rows.
4. **P011 small PDF-point overflows** — technically correct, possibly below Ester's practical “worth fixing” bar.
5. **References section** — P064 structural checks exist; Ester also cares about citation-style consistency with Bio Sketch publications (not fully automated).

---

## Source freshness and limitations

| Access attempt | Result |
|---|---|
| `origin/main` @ `668aa1b` | **Used** — includes PR #467 P011 presentation. |
| Google Sheet `1IohAmbslfX1orMDr7gx6oJyGGTqAV_AAtF31GP-57Gc` | **Not fetched** — no Drive-scoped credential in this environment (historical audits: HTTP 401 on CSV export). |
| Gmail feedback threads | **Not in repo** — secondhand via status docs only. |
| `data/raw/ester/260330_YESNO_audit_logic_matrix.xlsx` | **Used** — tracked local copy (2026-05-21 commit). |
| `results/ester_feedback_raw/formatting_rules.xlsx` | **Missing from repo** — referenced by `ester_p_rule_feedback.json` and `scripts/ester_rule_consistency_audit.py`; content partially mirrored in `data/specs/ester_p_rule_feedback.json`. |
| EF-annotated PDFs in `data/raw/ester/` | **Present (LFS)** — aggregate category counts only via `ester_feedback_examples.json` and evaluation docs; **no body text quoted here**. |

Findings that depend on the live Google Sheet or Gmail should be read as **“per repo transcription, not re-verified today.”**

---

## Source inventory

| File / artifact | Type | Date / context | Rules / topics informed | Current vs historical | Confidence as source of truth |
|---|---|---|---|---|---|
| `data/raw/ester/260330_YESNO_audit_logic_matrix.xlsx` | Ester YES/NO matrix | 2026-03-30 filename | Front matter, TOC, LoT, LoF atomics (Q001–Q079) | **Current best local matrix** | **High** (authoritative style; may lag Drive) |
| `data/specs/ester_q_matrix.json` | Repo transcription of matrix | Derived from xlsx | Q-rule questions/remediations | Current mirror | **High** for wording; verify against xlsx when sheet updates |
| `data/specs/ester_p_rule_feedback.json` | Ester Formatting Rules sheet (subset) | 2026; 19 P-rules with edits | P011–P018, P042–P045, P051, P055, P063, P067, P068, P074 | Current mirror; **missing live sheet** | **High** for edited P-rules; incomplete (no P035, P021, P026 edits in file) |
| `docs/status/ester_feedback_source_of_truth.md` | Maintainer synthesis | 2026-07-02+ | Language principles, P-rule notes | Current policy doc | **High** for intent; not implementation authority |
| `docs/status/ester_language_alignment_audit.md` | Wording audit | 2026-07-02 | P011–P055 presentation targets | Historical baseline; mostly still valid | **Medium** — pre–PR #467 for P011 job text |
| `docs/status/ester_current_wording_inventory.md` | Wording inventory | 2026-07-02 | Catalog vs job phrasing | Historical for P011 job cards | **Medium** |
| `docs/status/ester_policy_review_p021_p026.md` | Policy conflict record | 2026-07-03 | P021, P026 limits/families | **Current** | **High** for open policy questions |
| `data/processed/examples/ester_feedback_examples.json` | Extracted EF comment metadata | Yin Haotian 2nd review | Real comment categories (no body text) | Illustrative sample | **Medium** — one student; category counts only |
| `docs/sources/ester_materials.md` | Material index | 2026 | Dataset layout, permissions | Current | **High** for what exists in repo |
| `docs/evaluation/phase2_ester_comment_vs_tool_findings.md` | Tool vs comments | 2026-05-21 Yin PDF | P011 vs P013 volume vs EF categories | Historical evaluation | **Medium** — category-level only |
| `data/raw/guidelines/*` | NJIT guideline docs | Various | Margins, fonts, headings (not Ester-authored) | Institutional baseline | **High** for NJIT policy; **Medium** for Ester tone |
| `scripts/ester_rule_consistency_audit.py` | Automated audit script | Maintained | Cross-check specs vs catalog | **Blocked** — missing `results/ester_feedback_raw/` | N/A until xlsx path restored |
| Gmail / Drive originals | Primary sources | Ongoing | Wording reactions, product direction | **Missing locally** | **Highest** when available — not accessed here |

---

## Consistency status legend

| Status | Meaning |
|---|---|
| **aligned** | Criteria and student-facing language match Ester's binary style and intent. |
| **language mismatch** | Detection acceptable; question/remediation/fix wording differs from Ester's sheet/matrix. |
| **criteria mismatch** | Warns for different things, or uses different limits, than Ester's source. |
| **too strict** | Technically defensible but likely stricter than Ester's practical review or sheet intent. |
| **too lenient** | Ester would flag; tool misses or under-warns. |
| **unclear / needs Ester decision** | Repo transcription ambiguous or policy conflict. |
| **missing source** | No Ester row or comment evidence for this topic in available materials. |

---

## Rule-by-rule consistency matrix (priority topics)

### P011 — margin containment (post–PR #467)

| Field | Detail |
|---|---|
| **Ester / source expectation** | `ester_p_rule_feedback.json`: binary question *“Is all text contained entirely within the required page margins?”*; remediation: set 1.5″ left, 1″ other margins. Source-of-truth doc: **strict** — no text/tables/figures in margins. Yin EF comment (page 10): *“This is in the margins!”* (visual, not point-based). |
| **Current system behavior** | `pdf_margins.py`: left 1.5″ / others 1″; flags line overflow **> 3 pt**; artifact guard for compressed-PDF shifts; per-side findings with `worst_overflow_pt`, `highlight_bboxes`, `margin_boundary_bbox`; PR #467 adds `page_context`, `margin_content_kind`, context-aware `suggested_fix` via `p011_margin_presentation.py`. |
| **Status** | **mostly aligned** (criteria); **language mismatch** (remediation); **too strict** (borderline pt-level); **too lenient** (non-text floats) |
| **Evidence** | `data/specs/ester_p_rule_feedback.json` (P011); `src/njit_auditor/rules/pdf_margins.py`; `src/njit_auditor/p011_margin_presentation.py`; `ester_feedback_examples.json` (margin comment category) |
| **Affected user-facing text** | Job cards: *“{Abstract/References/…} content on page N appears to cross the required {side} boundary…”*; suggested fixes: paragraph/hanging-indent/approval-date strings (not Ester's inch-setting sentence). |
| **Recommended action** | **Ask Ester:** keep context-specific fixes vs revert to sheet remediation? **Ask Ester:** minimum visible overflow worth a student warning? **Implementation (later):** optional high-confidence-only student filter; detector metadata for table/figure image boxes (highlight plan). |

### P013 — visible page number position

| Field | Detail |
|---|---|
| **Ester / source expectation** | Sheet edit: bottom-center, 0.5″ from bottom. Matrix: per-page no-number checks (Q001, Q008, Q012, Q014) are separate from body numbering style. |
| **Current system behavior** | Emits `page_number_candidate` warnings for margin-zone numeric text; job text frames as verification signal; high volume on EF Yin clean PDF evaluation (**113** findings vs **1** margin comment). |
| **Status** | **language mismatch** (umbrella fallback text); **too strict** (candidate noise on EF-annotated workflows) |
| **Evidence** | `ester_p_rule_feedback.json` (P013); `phase2_ester_comment_vs_tool_findings.md`; retained branch `fix/page-numbering-false-positives` |
| **Affected user-facing text** | `/rules` override is Ester-aligned; job/drilldown fallbacks still mention sequence/style bundle. |
| **Recommended action** | Cherry-pick from retained `fix/page-numbering-false-positives` after isolated review; align job fallback to bottom-center binary only; route sequence issues to P028/P029/P037 cards. |

### P019 / P028 / P029 / P037 — page numbering family

| Field | Detail |
|---|---|
| **Ester / source expectation** | Split front-matter vs body pagination (P019 sheet edit); matrix Roman sequence per section (Q022, Q031, Q035, Q046, Q060, …). |
| **Current system behavior** | P028/P029/P037 atomics largely wording-aligned; P019 umbrella question still *“candidates…obvious inconsistencies”*; P037 uses **dynamic** expected Roman (PR #407), while catalog text still lists fixed template numerals. |
| **Status** | **partially aligned**; **language mismatch** (P019 umbrella, P037 catalog vs behavior); **too strict** (P019 on EF PDFs per P073 triage notes) |
| **Evidence** | `ester_language_alignment_audit.md`; `ester_q_matrix.json`; `project_added_rules.json` (P019, P037) |
| **Recommended action** | Presentation-only: retire P019 umbrella student text in favor of P028/P029/P037 atomics; update P037 catalog question to describe computed expectation (wording-only). |

### P014 — front-matter heading layout

| Field | Detail |
|---|---|
| **Ester / source expectation** | One binary per page (Q013, Q021, Q036, Q047, Q061, Q070, …) — all caps, bold, centered, top. |
| **Current system behavior** | Single catalog question; detector emits per-heading/`source_q_rule_id` findings; **no P014A–F public cards** on `/rules`. |
| **Status** | **criteria mismatch** (presentation); detector **mostly aligned** |
| **Evidence** | `ester_p_rule_feedback.json` (P014); `ester_broad_rule_atomic_mapping.md` |
| **Recommended action** | Implement P014 presentation-split prototype (lowest-risk broad split per prior audit). |

### P015 / P043 / P044 — indentation

| Field | Detail |
|---|---|
| **Ester / source expectation** | Split front matter (Abstract Q002/Q003, Ack Q044/Q045) from body (two proposed body questions in sheet). |
| **Current system behavior** | P015A/B public cards; P043/P044 atomic rules; detector skips Abstract/Ack on P015 body rule; tests `test_p015_body_indent_ester_split.py`, `test_ester_p014_p015_atomic_split.py`. |
| **Status** | **mostly aligned**; **language mismatch** (parent P015 still exists internally) |
| **Evidence** | `ester_p_rule_feedback.json` (P015); Ester comments: *“delete indent”* (recurrent) |
| **Recommended action** | Verify every job card routes to P015A/B or P043/P044 reference; consider student-visible split for mid-sentence paragraph breaks (comment category — **not** a current rule). |

### P016 / P023 — spacing

| Field | Detail |
|---|---|
| **Ester / source expectation** | P016 sheet: no blank lines; text flows top-to-bottom. P023: double-spaced body Ch.1–References with named exceptions. |
| **Current system behavior** | P023 catalog + remediation list exceptions (aligned in Slice 1). P016 heuristic blank-line / vertical gap warnings. EF comments: *“delete blank line and indent”*, *“text must be continuous”*. |
| **Status** | **P023 aligned**; **P016 partially aligned** — Ester cares about blank lines inside sections; P016 may not match her phrasing |
| **Evidence** | `ester_p_rule_feedback.json` (P016); `ester_feedback_examples.json` (spacing_blank_lines) |
| **Recommended action** | Wording-only pass on P016 to mirror Ester's “continuous text / no blank lines” language; no threshold change without Ester confirmation. |

### P020 / P027 — capitalization & headings

| Field | Detail |
|---|---|
| **Ester / source expectation** | Separate binaries per heading level (P020 sheet); numbered heading levels in matrix via P027 family. EF: *“Level three (X.x.x) uses sentence case”*. |
| **Current system behavior** | P020 single umbrella; P027 per-level `issue_type`s; PR #407 bold-heading gate. |
| **Status** | **language mismatch** / **presentation-split-needed** |
| **Evidence** | `ester_p_rule_feedback.json` (P020); `ester_feedback_examples.json` (heading_title) |
| **Recommended action** | Presentation split P020 by level/context; keep P027 as owner for numbered headings. |

### P035 — table/figure centering

| Field | Detail |
|---|---|
| **Ester / source expectation** | **No row in `ester_p_rule_feedback.json`.** Ester comments mention table titles (title case, no period) — closer to P017 than P035. Centering implied by NJIT layout norms. |
| **Current system behavior** | Text-layer float heuristic; skips image-only floats; caption above/below checks. |
| **Status** | **missing source** for P035 specifically; **too lenient** on image-only pages; **unclear** on centering tolerance |
| **Evidence** | `docs/planning/p035_scope_and_design.md`; retained `fix/p035-table-centering-presentation` |
| **Recommended action** | Ask Ester whether centering warnings should be student-facing or advisor-only; isolate presentation branch before merge. |

### P040 / P053 / P054 — list punctuation

| Field | Detail |
|---|---|
| **Ester / source expectation** | LoF terminal punctuation (Q075 analog); LoT/TOC no terminal period. |
| **Current system behavior** | Atomic questions; Slice 2 wording aligned; highlights on P040/P053/P054 entries. |
| **Status** | **aligned** |
| **Evidence** | `ester_language_alignment_audit.md`; `test_ester_rule_wording_pass1.py` |
| **Recommended action** | Maintain; preserve entry-index presentation from PR #407. |

### P068 — approval page structure

| Field | Detail |
|---|---|
| **Ester / source expectation** | Sheet: advisor role + signature/date blocks; manual review for honorifics/rank (Q015–Q020 **not** implemented in P068). EF comments: rank order, city/state for external members, NJIT abbreviation — **semantic**, not structural. |
| **Current system behavior** | Structural heuristic; PR #466 accepts `Thesis Advisor` label; no bbox highlights. |
| **Status** | **aligned** for structural scope; **too lenient** for Q015 honorifics / rank order; **language mismatch** on truncated sheet remediation text |
| **Evidence** | `ester_p_rule_feedback.json` (P068); `ester_feedback_examples.json` (committee_approval_page) |
| **Recommended action** | Do **not** expand P068 to honorifics without Ester policy sign-off; keep semantic committee comments as manual-review territory. |

### References — indentation, spacing, labelling

| Field | Detail |
|---|---|
| **Ester / source expectation** | EF: section must be titled *REFERENCES*; publications must match reference formatting; hanging indent for bibliography entries (analogous to Q029 bio sketch). No dedicated references Q-row in YES/NO matrix. |
| **Current system behavior** | P064: heading detection, indent/spacing consistency heuristics; PR #467 P011 suggests hanging-indent fix on references pages when margin context inferred. |
| **Status** | **partially aligned**; **too lenient** on citation-style match to Bio Sketch; **language mismatch** — P011 fix is layout-margin, not citation-style |
| **Evidence** | `pdf_references_citations_structural.py`; `p011_margin_presentation.py`; `ester_feedback_examples.json` (references) |
| **Recommended action** | Ask Ester whether references warnings should separate **margin/layout** vs **citation style**; consider presentation-only card for P064 vs P011 overlap on references pages. |

### P021 — abstract word count (policy)

| Field | Detail |
|---|---|
| **Ester / source expectation** | Transcribed sheet: MS ≤200, PhD ≤400; separate binaries. |
| **Current system behavior** | MS ≤150, PhD ≤350; single combined question. |
| **Status** | **criteria mismatch** / **unclear / needs Ester decision** |
| **Evidence** | `ester_policy_review_p021_p026.md` |
| **Recommended action** | **No change** until Ester confirms official limits. |

### P026 — font family/size (policy)

| Field | Detail |
|---|---|
| **Ester / source expectation** | Times New Roman, Arial, Computer Modern family; 12pt except tables/figures. |
| **Current system behavior** | Accepts Latin Modern + serif aliases; 11–13pt tolerance; page-level 50% fraction gate; P026A/B split on `/rules`. |
| **Status** | **mostly aligned** wording; **too lenient** vs literal 3-family list if Ester intended strict list |
| **Evidence** | `ester_policy_review_p021_p026.md`; `test_p026_font_policy_ester_consistency.py` |
| **Recommended action** | Confirm alias list with Ester before tightening detectors. |

---

## Additional rules (summary rows)

| Rule(s) | Status | Note |
|---|---|---|
| P012 | aligned | Ester: no edit requested |
| P017 | presentation-split-needed | Figure vs table groups in sheet; issue_types exist |
| P018 / P024 / P030–P032 / P036 / P039 / P046–P050 | mostly aligned wording; presentation-split-needed on job cards | `/rules` P018A–Q delegation ahead of job UI |
| P022 | mostly aligned | Page-specific findings; could tighten to matrix question text |
| P025 | presentation-split-needed | DC wrapper notice behavior must stay non-problem |
| P041, P042, P045, P047, P051, P052, P055, P063, P066, P067, P074, P078 | aligned (wording slices) | Per prior audits |
| P064 | partially aligned | References structural only |
| P084+ | out of scope | Not started |

---

## Top inconsistencies (ranked)

1. **P021 / P026 policy constants** — documented conflicts; wrong student advice if “fixed” without Ester.
2. **Page-numbering noise (P013 + P019)** — tool volume >> EF margin/indent comments on Yin evaluation PDF.
3. **Broad-rule student cards** — one warning still maps to many matrix questions (P014, P018, P019, P020, P024, P025).
4. **P011 point-level strictness** — 3pt tolerance + low-confidence small overflows vs Ester's visual margin comments.
5. **P011 non-text geometry** — text-layer detection misses image/table bodies Ester would judge visually.
6. **P011 suggested-fix wording (PR #467)** — context fixes not in Ester's sheet remediation (may still be pedagogically better).
7. **Approval-page semantics (Q015–Q020)** — EF comments on rank/honorifics/city not covered; P068 structural only.
8. **References citation-style consistency** — EF explicit; P064 only partial.
9. **Missing `formatting_rules.xlsx` in repo** — blocks automated `ester_rule_consistency_audit.py` refresh.
10. **P035 centering** — no Ester P-rule edit on file; detector scope unclear vs her expectations.

---

## Language mismatches (student-facing)

| Area | Ester style | Current drift |
|---|---|---|
| P011 suggested fix | Inch settings (sheet) | Context-specific layout verbs (PR #467) |
| P011 job headline | Binary containment question | “Appears to cross…” + strict note (acceptable hedge) |
| P013 job fallback | Bottom-center 0.5″ binary | Sequence/style bundle language |
| P019 catalog | Per-regime binaries | “Candidates…obvious inconsistencies” |
| P020 catalog | Per-level binaries | “Title-case heuristics” (stripped on `/rules` only) |
| P037 catalog | Sequential Roman after prior section | Fixed template numerals (iv, vii, viii) in catalog text |
| P026 job fallback | Three named families | Sometimes omits Arial in older fallback paths (verify live job template uses P026A override) |
| Broad cards | One issue = one question | Umbrella `rule_id` on job cards for P018/P024/P032/P036 |

---

## Criteria / strictness mismatches

| Rule | Stricter or looser? | Detail |
|---|---|---|
| P011 | **Stricter** (mechanical) | Warns on >3pt text overflow; low confidence ≤4pt still shown |
| P011 | **Looser** (coverage) | No full float/image margin check |
| P013 | **Stricter** | Candidate detection >> human comment frequency in Yin eval |
| P019 | **Stricter** | Umbrella inconsistency checks on noisy PDFs |
| P021 | **Stricter** | Limits lower than transcribed sheet → more warnings |
| P026 | **Looser** | Extra accepted families and ±1pt size tolerance |
| P035 | **Looser** | Skips image-only floats |
| P068 | **Looser** | No honorific/rank/location semantics |
| P064 | **Looser** | No citation-style parity with Bio Sketch |

---

## Evidence / highlight consistency

| Topic | Ester would point to… | Current tool |
|---|---|---|
| Margin text overflow | Visible line in margin | Tight per-adjacent-group boxes + margin-boundary guide (good) |
| Margin table/figure | Full object extent | Text lines only; image boxes skipped |
| Page numbers | Exact printed numeral | Candidate text in margin zones (can over-highlight) |
| TOC/List entries | Specific entry line | Entry-level bbox on P040/P053/P054; column-level gaps on P046/P048 |
| Approval page | Committee block / date line | No highlight; structural counts only |
| References | Entry hanging indent / style | P064 geometry; P011 margin overlay on violating lines |

**Location labels:** Page-order sort + sub-page labels (P011 side, P027 heading, etc.) are **mostly aligned** with Ester's page-by-page review; advanced/internal keys (`issue_type`, `triage_tier`) are not student-facing.

---

## UI / report flow vs Ester workflow

| Ester practice | Current UI | Consistency |
|---|---|---|
| Review front matter page-by-page | Findings in page order + location labels | **aligned** |
| One formatting question at a time | Compact cards; broad rules still group | **partial** |
| Binary yes/no + one fix | Suggested fix + polished comment | **mostly aligned** post-slices |
| Distinguish “must fix” vs “check” | Confidence badge (High/Medium/Low) | **aligned** — confirm with Ester |
| Download marked PDF | Highlighted PDF per page | **aligned** |
| Internal triage | Advanced collapsed section | **aligned** — does not leak to students by default |

---

## Questions for Ester (send as a short review packet)

1. **P011 thresholds:** Should students see warnings for text only **1–4 pt** past the margin, or only clearly visible overflows?
2. **P011 remediation (PR #467):** Do you prefer the sheet’s inch-setting remediation, or context-specific fixes (hanging indent on references, approval date layout, etc.)?
3. **P011 non-text content:** Should margin checks eventually include figure/table **images**, not just text lines?
4. **P021 limits:** Confirm official MS/PhD abstract word limits (150/350 vs 200/400).
5. **P026 fonts:** Are Latin Modern and near-equivalent TeX serifs acceptable for final submission?
6. **P013 page-number candidates:** Should students see “candidate” page-number warnings, or only definitive bottom-center violations?
7. **Borderline spacing (P016/P023/P036):** Warnings vs low-confidence “worth checking” for gap-heuristic findings?
8. **Approval page:** Should honorifics (Dr./Mr./Ms.), rank order, and external member city/state be in scope for automated warnings, or stay manual?
9. **References:** Separate warnings for **margin/layout** vs **citation-style consistency** with Bio Sketch publications?
10. **P035 table/figure centering:** Is horizontal centering drift a student-facing warning or advisor-only note?
11. **Confidence display:** Should low-confidence margin/spacing warnings be hidden from students unless they opt into “show all”?
12. **Wording preference:** Approve context labels like “References content” vs generic “thesis content” on margin cards?

---

## Recommended next implementation slices (after Ester answers)

| Priority | Slice | Type | Rules |
|---|---|---|---|
| P1 | Page-numbering FP bundle | detector + presentation | P013, P019 (from retained branch, isolated) |
| P1 | P014 presentation split | presentation-only | P014 → Q-row cards |
| P2 | P011 policy confirmation | presentation or threshold | P011 — only after Q1–Q3 answered |
| P2 | P019 umbrella retirement | presentation-only | Route to P028/P029/P037 |
| P2 | P037 catalog wording | wording-only | Describe dynamic Roman expectation |
| P3 | P021/P026 policy merge | detector + wording | After written confirmation |
| P3 | P035 presentation | presentation | From retained branch |
| P3 | Restore `formatting_rules.xlsx` mirror | docs/specs | Unblock `ester_rule_consistency_audit.py` |

**Explicitly defer:** P084; broad detector splits without golden comparison; merging retained WIP branches wholesale.

---

## Validation note (this pass)

Docs-only changes. Run `ruff check .`, `mypy src`, `python -m pytest` after status doc updates (manifest-aligned pytest count unchanged).

**Live deployment:** untouched (may remain at `c0d1199` while `main` is `668aa1b`).
