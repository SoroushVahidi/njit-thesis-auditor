# Stage 1 policy reconciliation — 2026-11-10

Ester's November 9 feedback explicitly requires **figure descriptions in sentence
case**, including the List of Figures (private assessment F18). This supersedes
the October 5/6 title-case interpretation recorded in the historical status notes.
Table titles retain Title Case; TOC levels retain their existing requirements.
No R055 prefix policy is changed.

R024E remains the public card. Its internal `list_of_figures_title_case` subtype
is retained for compatibility; new findings identify excess capitalization and
request sentence case. The detector conservatively recognizes clear Title Case,
preserves document-supported proper names and acronyms, and abstains on ambiguous
short descriptions, mixed-case scientific descriptions and technical notation.
It is not complete grammatical or proper-name validation. P017 continues to delegate LoF capitalization to P024.

F01/F12/F20 establish page ownership defects, not a new numbering policy.
Unnumbered Abstract continuations cannot anchor the Roman sequence. Title,
copyright and approval roles are identified before sequence checks; P037 retains
the Biographical Sketch iv anchor and checks genuinely incorrect anchors. R029
uses plausible primary folios rather than every Roman-looking token on a page.

Original student documents, reviewer material and detailed evidence remain in
private task notes outside Git. Only generic synthetic regression text is added.

F09 receives bounded structural review in R060 when parent, sibling, numbering
and indentation agree on a possible missing dot. R024 defers capitalization for
that entry; valid two-digit Level 2 entries retain their capitalization checks.
This is not a complete malformed-number validator. F25/F26 use section-specific
presentation categories and actions; historical coarse evaluation categories
and rule identifiers remain stable. Missing section metadata retains the shared
fallback category. The wider R035 terminology/geometry work belongs to Stage 2.
