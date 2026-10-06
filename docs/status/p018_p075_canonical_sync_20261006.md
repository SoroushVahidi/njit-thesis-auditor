# P018/P075 Canonical Sync and Q052 Routing (2026-10-06)

**Base:** `fix/public-card-ownership-and-r028-authority-20261006` at `a385c3b`
(see `public_card_ownership_and_r028_authority_20261006.md`).
**Authorization:** explicit approval to edit canonical JSON for P018 and P075
only. No other canonical record changed.

## Authority

- Q052 (Ester's matrix): "Every TOC entry must connect to a right-aligned page
  number using one consistent leader style." Same as the NJIT guideline's
  Table of Contents bullet.
- Ester's own P018 breakdown (`data/specs/ester_p_rule_feedback.json`) puts
  Q052 ("1d") in the **TOC** group only. Her List of Tables and List of
  Figures groups contain spacing, number-column and page-number-column rows
  (Q067–Q069, Q077–Q079), with no presence or leader row.
- So: TOC page-number presence and alignment → R075 (the public TOC card for
  Q052). LoT/LoF page-number column → R018N/R018Q. A LoT/LoF missing page
  number has no authority and stays unmapped.
- R018D (LoT/LoF leader style) carries Q052 as a project extension of the TOC
  row. That card and its `inconsistent_leader_dots` routing are unchanged.

## Canonical changes (`data/processed/rules/project_added_rules.json`)

- **P075** `rule_definition` now names entries missing their page number and
  page numbers out of the right-aligned column (previously only a web
  override said this; the override is removed). `remediation` is unchanged: it is already Ester's
  Q052 wording. `notes` record that P018
  TOC page-number findings link to this card. `issue_types` and
  `source_q_rule_ids` unchanged (they list P075's own detector output).
- **P018** `remediation` separates LoT/LoF leaders (P018D) from TOC leader
  style and page numbers (P075), and states the LoT/LoF page-number column
  and unmapped missing-page-number split. `notes` record the same.

## Q052 routing defect

`_resolve_p018_public_card` consulted the source-Q table first, for any rule.
P075's own findings cite Q052, so they would resolve to R018D, the LoT/LoF
leader card. The same latent misroute existed for P054 (TOC terminal period,
Q050 → R018B) and P063 (body appendix headings, Q058/Q059 → R018J/K).

It is latent, not live: every current link path (job page, problem groups,
text report) receives details with `source_q_rule_id` stripped by the student
export. It would surface as soon as the key reached the resolver.

Fix (mapping code only):

1. context-specific page-number routing first (TOC → P075; LoT/LoF column →
   P018N/Q; LoT/LoF missing page number → explicitly unmapped);
2. source-Q table, **only for the P018 family** (P018 and its delegated
   parents P024, P032, P036, P039, P042, P046, P048);
3. issue-type tables;
4. the rule's own public card, else nothing for hidden parents.

Every legitimate Q route comes from the P018 family, so none changes.

## Verification

- Seven-document raw findings byte-identical to the base (P018 19, P075 3,
  P019 0, P048 0).
- `scripts/ester_rule_consistency_audit.py`: identical status counts and
  identical P018/Q052/Q069/Q079 rows before and after.

## Not changed

- `data/specs/q_rule_coverage_report.json` (generated) still lists only P018
  under Q052; regenerating it would touch unrelated rows. Follow-up.
- Ester's historical feedback records; P015 continuation-indent policy;
  LoT/LoF `missing_page_number` (still unmapped); R045; R011; P001–P010;
  P055; P068.
