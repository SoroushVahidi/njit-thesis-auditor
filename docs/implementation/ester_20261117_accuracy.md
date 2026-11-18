# November 17 heading and figure context corrections

R024/P024 recognized only numeric chapter prefixes. An appendix entry such as
`B.1.7 Detailed synthetic results` therefore fell through to indentation-based
classification and could receive level-2 title-case advice. An appendix letter
occupies the chapter component: `B.1` is level 2, `B.1.7` is level 3, and deeper
numbers remain outside TOC capitalization scope. Explicit depth takes precedence
over indentation. The body heading classifiers P020/P027 use the same letter-root
semantics, including split number/title extraction. Existing evidence thresholds,
proper-name handling, and ordinary numbered chapter behavior are retained.

Authority: the repository's `Titles Examples Level 1 to 5.docx` and formatting
guidelines specify title case for X.x and sentence case for X.x.x; levels 4–5 are
not included in the TOC. Ester's November 17 clarification confirms that appendix
letters occupy X. This does not assign a new hierarchy to arbitrary alphabetic
list markers, version strings, or numeric prose.

R055/P055 incorrectly treated every numeric-only List of Figures entry as missing
Figure. Ester's November 17 clarification supersedes that interpretation: Figure
is required in body references, not before each LoF entry. Q072's Figure column
header is still checked separately by P031/P050. Wrong-list entries, LoT prefix
checks, caption punctuation/case, and numbering checks remain active.

P055 now accepts numeric-only LoF entries and checks explicit abbreviated body
references, such as `see Fig. 2.1` or `Fig. 2.1 shows ...`. This adds narrow body
coverage that the previous list-only detector did not provide. It excludes
detected TOC/list pages and captions, and never infers references from bare
numbers. Short same-block wraps can separate Fig. from its number; pages are not
joined. Ambiguous references still require manual review. The legacy LoF subtype
is not emitted; its display guidance explains that the prefix is optional.

Synthetic coverage includes appendix and numeric depths, continued/wrapped TOC
entries, split and glued number extraction, genuine capitalization violations,
non-heading numbers, LoF/list/caption/body distinctions, retained wrong-list and
geometry evidence, real generated PDF extraction, and JSON/report advice.
Historical R055 geometry/segmentation tests now use still-invalid LoT or misplaced
entries, preserving their assertions rather than retaining an obsolete LoF policy.
Private comparison outputs and validation logs belong outside Git. This change
has no analytics, database, deployment, or activation dependency.
