# Ester Next Review Set (2026-09-02)

This is the complete unresolved policy follow-up set after the closure audit.
Resolved items, including R016 and R019, are intentionally excluded.

## R035 - Figure/table centering and caption position

**Package:** `docs/evaluation/ester_feedback/R035_Ester_Auditor_Feedback.xlsx`
and `docs/evaluation/ester_feedback/R035_Ester_Auditor_Feedback.pdf`

**Question for Ester:** For the selected evidence, is the auditor's judgment
that the figure/table float is not centered within the text area, or that the
caption is in the wrong position, correct?

**Examples:** The current deterministic selections are Anthony, physical PDF
page 60, `table_body_not_centered`, and Praneeth, physical PDF page 29,
`figure_body_not_centered`. These are the only current positive examples; no
behavior was changed pending a human judgment about the shown geometry.

**Why human judgment is required:** The detector has measurable geometry, but
the expected centering and caption-position tolerance is a formatting-policy
judgment for these layouts.

## R036 - TOC/List inter-entry spacing

**Package:** `docs/evaluation/ester_feedback/R036_Ester_Auditor_Feedback.xlsx`
and `docs/evaluation/ester_feedback/R036_Ester_Auditor_Feedback.pdf`

**Question for Ester:** For the selected boundary evidence, should the visible
spacing between these consecutive TOC/List entries be treated as a formatting
violation under this rule?

**Examples:** The current deterministic weakest examples are Philip, physical
PDF page 11; Muyeed, page 10; Anthony, page 12; Praneeth, page 11; Patrick,
page 7; and Youra, page 12. The selected findings are
`toc_inter_entry_spacing_too_tight`; Sebastian has no current R036 finding.
The package contains one row per dissertation, with the weakest surviving
finding where one exists.

**Why human judgment is required:** The parser measures entry-to-entry gaps and
handles wrapped entries, but the acceptability of the residual dot-leader and
continuation-line spacing requires Ester's formatting judgment.

## R055 - Cross-type List numbering labels

**Package:** `docs/evaluation/ester_feedback/R055_Ester_Auditor_Feedback.xlsx`
and `docs/evaluation/ester_feedback/R055_Ester_Auditor_Feedback.pdf`

**Question for Ester:** When a List of Tables or List of Figures entry exposes
only a numeric label, without an explicit `Table` or `Figure` prefix, is that
numeric-only label sufficient to determine whether the entry belongs to the
correct list and numbering format?

**Evidence:** The current detector produces no positive R055 findings for the
seven dissertations. Many extracted list entries begin with numeric labels
such as `1.1` or `1`, so the detector deliberately does not infer the object
type from the number alone. See the representative, non-finding context note
at `docs/evaluation/ester_feedback/R055_numeric_only_context_20260902.md`.
The question is whether that conservative gate is the intended policy, not
whether zero findings prove compliance.

**Why human judgment is required:** The available PDF evidence does not expose
an explicit object-type prefix for many entries, and broadening the classifier
would require a policy decision rather than a demonstrated parsing fix.

No live Google Sheet or external package was modified. Existing R035, R036,
and R055 packages are referenced without timestamp-only regeneration.
