# P029 Roman Numeral Sequence Evaluation (Phase 2)

Purpose

- Validate conservative checks for lowercase Roman numeral ordering within front-matter pages (i, ii, iii...).

Q-rule basis

- Q022, Q031, Q035, Q046, Q060

Relation to other rules

- P028: checks page-numbering regime (Roman vs Arabic). P029 checks ordering within front-matter only.
- P013/P019: candidate detection and global page-number consistency provide inputs; P029 reuses page-number candidates.

Roman numeral conversion/behavior

- Only considers candidates classified as `roman_lower` within pages classified as `front_matter`.
- Skips named no-number pages (Abstract, Title, Approval, Copyright) and pages with explicit no-number signals.
- Requires ≥2 visible roman candidates to run sequence checks.
- Flags: `roman_sequence_gap` (non-consecutive), `roman_sequence_repeat` (same value on adjacent visible pages), `roman_sequence_decrease` (value decrease).
- Findings include: issue_type, candidate_text, candidate_value, previous_value, expected_value, page_region, confidence.

Synthetic test summary

- Added synthetic tests covering:
  1. i, ii, iii → no warning
  2. i, iii → roman_sequence_gap
  3. i, ii, ii → roman_sequence_repeat
  4. iii, ii → roman_sequence_decrease
  5. Too few roman candidates (1) → no warning
  6. Arabic front-matter handled by P028 (P029 ignores Arabic)
  7. Body Roman numerals ignored by P029 (P028 covers body style)
  8. No-number title/abstract/approval pages do not cause sequence gap
  9. Roman numeral inside TOC entry text is ignored
  10. CLI `njit-audit pdf` output includes P029 when triggered
  11. JSON/Markdown report includes P029 when triggered
  12. Grouped summary handles repeated P029 warnings when threshold reached (tested)

Evaluation counts by file

(Sources: data/evaluation/generated/p029_roman_sequence/*.json)

- Yin_H_4th_Review_with_EF_comments_compressed.pdf.json: 12 findings (all `roman_sequence_repeat`)
- Yin_Haotian_Second_R_with_EF_Feedback.pdf.json: 0 findings
- 250218_Cibaku_Elson_First_Review.pdf.json: 0 findings
- 260415_Yin_H__2nd_review_with_EF_Comments.pdf.json: 0 findings

Overlap with P028

- Yin_H_4th_Review_with_EF_comments_compressed: P029 findings overlap with P028 (mixed regime present)
- Other files: no overlap detected

Clean baseline impact

- Sebastian Fine baseline (clean dissertation) was run: P029 findings are low/0 on clean baseline (no sequence warnings observed).

Limitations / Caveats

- Conservative heuristics: only visible-numbered pages are compared; hidden or unextractable numbers are ignored.
- Requires reliable named front-matter headings or body CHAPTER detection to classify front matter.
- TOC numeral tokens are ignored where they appear embedded in TOC entry text, but false positives remain possible if OCR/text layer is noisy.
- Does not attempt to infer missing/hidden pages; only flags visible-number anomalies.

No dissertation body text is quoted in this document.
