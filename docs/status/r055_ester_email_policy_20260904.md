# R055: Reviewer guidance and policy provenance

## Distinct sources and requirements

| Source | What it establishes | Limit |
| --- | --- | --- |
| Published NJIT formatting material and the supplied YES/NO matrix, Q063/Q072 | The left column labels are respectively Table and Figure, bold and left-aligned beneath the list heading. | These matrix questions do not themselves require a repeated word before every entry number. |
| Ester Flaim's written reviewer clarification, September 4, 2026 | Each List of Tables or List of Figures entry should include its applicable Table or Figure word before the X.x number. | This is later reviewer guidance applied by this project, not evidence of a formally published university-wide policy revision. |
| Current P055 implementation at baseline `4efd780dde53eea907a714df8bfed86e923ef86a` | Separately reports a complete entry naming the wrong object type, or a numeric-only entry lacking the applicable word. | PDF extraction and conservative gates limit which entries can be evaluated; findings still require case review. |

The reviewer clarification supplements the matrix's column-heading requirements.
A correct column heading does not satisfy the separate entry-prefix requirement.
Conversely, correctly prefixed entries do not satisfy a missing or incorrectly
styled column heading. P031 checks header presence/coarse alignment; P049/P050
check header alignment and bold style. P055 does not replace those checks.

## Provenance and access limitation

Minimal source metadata: reviewer **Ester Flaim**, written guidance dated
**September 4, 2026**, stable project reference **`R055@email:2026-09-04`**.
The original message was independently inspected through an authorized,
configured integration during this reconciliation. Its immediate context is
a direct answer about R055 list-entry type, rather than a judgment on an
individual finding or a revision to the published matrix.

Earlier versions of this record relied on the repository owner's report of
that message. The original remains private and is not stored in this checkout.
An offline reader cannot independently inspect it without authorized access
or verification by its custodian. This record provides only a policy paraphrase
and minimal provenance; it does not reproduce the email, headers, private
message identifiers, private URLs, or unrelated correspondence.

The September 2 authority snapshot's "NO ESTER DECISION FOUND" entry describes
the sources available at that earlier date. It does not negate the later
clarification. The June 5 [original scope](../planning/p055_scope_and_design.md)
also predates the prefix clarification and describes the original cross-type
check rather than the complete current behavior.

## Actual behavior and correction guidance

- Correctly prefixed Table entries in the List of Tables and Figure entries in
  the List of Figures do not trigger P055.
- Numeric-only entries can trigger `lot_entry_missing_table_prefix` or
  `lof_entry_missing_figure_prefix`. The correction is to add the applicable
  word before the number, not to move the entry into another list.
- A Figure entry in the List of Tables or Table entry in the List of Figures
  can trigger `lot_entry_is_figure` or `lof_entry_is_table`. That is a separate
  wrong-list correction, not a request merely to add a missing prefix.
- Existing gates remain: list-page detection, at least two extracted entries,
  a page-number token, sufficient entry text, and a recognizable prefix pattern.
  Incomplete or ambiguous extraction is not proof of noncompliance.

Existing `source_q_rule_id` values Q063/Q072 identify related list context;
they are not complete provenance for the per-entry prefix requirement. Its
specific basis is the later reviewer clarification above. This reconciliation
does not change those serialized fields, any detector logic, or student wording.

## Correction to the earlier accuracy evaluation

The earlier evaluation omitted this later guidance and incorrectly described
numeric-prefix enforcement as unsupported. Its counts must be interpreted as
follows; the detector is not being disabled to make older examples pass:

- **26 warnings on the supplied historical mock front matter:** a conflict
  between that older example and the later reviewer guidance, not 26 confirmed
  false positives. The example can still illustrate column headings without
  being a complete compliance oracle for subsequent reviewer clarification.
- **Six warnings on six synthetic numeric-only entries with correct headers:**
  expected entry-prefix findings under the later guidance, not six confirmed
  false positives. Correct headers and correct entry prefixes are independent.
- **277 records across eight of nine private PDF versions:** unadjudicated
  findings requiring individual case review. Neither the policy clarification
  nor this count establishes that all 277 are true positives or false positives.

Those private-corpus counts are historical measurements from the preceding
evaluation, not a fresh private-document rerun in this reconciliation. No
precision or recall estimate follows from them.

## Historical judgments remain separate

The historical sheet export had no populated R055 finding rows to adjudicate;
"No current auditor R055 finding" describes auditor state, not a reviewer
verdict. The ledger therefore records this guidance as a policy resolution
with `case_id=None` and `policy_reference="R055@email:2026-09-04"` through
`importers.known_policies`. It is not a case-level TRUE_VIOLATION or
FALSE_POSITIVE and must not increase reviewed-case accuracy totals.

No matrix contents, historical adjudications, policy-resolution records,
private student documents, or detector behavior are changed by this update.
