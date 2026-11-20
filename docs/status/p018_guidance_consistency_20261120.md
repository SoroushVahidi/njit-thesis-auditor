# P018 continuation guidance consistency — November 20, 2026

Base: `598bcd9b5d072ddf2143e609fe1c24ee126dd68f`.

The comprehensive November 20 feedback audit identified F23 as a presentation
contradiction. The validated detector already accepts valid rightward indentation
of second and third TOC title lines and retains genuine leftward violations.
Its student-facing guidance still applied the September symmetric interpretation:

- `toc_list_student_preview.py`, `polished_comments.py`, `report_view.py` and
  `issue_type_explanations.py` prohibited continuation lines being “indented past”
  the title text.
- `finding_explanations.py` said “neither left of it nor indented past it.”
- The public R018R card in `web_app.py` required every wrapped line to start
  “directly under” the first word, without the later indentation allowance.

`p018_guidance.py` now supplies shared correction text: move the affected
continuation to the first word of the title text or farther right; valid rightward
indentation of second and third lines is accepted. Short observations, detailed
explanations, issue help and R018R describe the directional condition consistently.
A continuation starting under the section number, farther left, or between the
number and title text remains a supported violation when it exceeds the detector's
existing tolerance. A single-line entry has no continuation to check.

This applies to the existing numbered Table of Contents continuation check. It
does not extend that check to Lists of Tables/Figures, impose a new maximum indent,
or alter hierarchy indentation, leaders, page-number columns or spacing rules.
The processed umbrella catalog has no contradictory directional instruction and
is unchanged. Generic report templates consume the corrected shared presentation.
Original and highlighted PDFs display source pages; the combined PDF appends the
corrected guidance. Source text and highlighting geometry are preserved.

No detector module, threshold, severity, finding generation or raw evidence message
changed. The older September implementation note is explicitly marked as historical
where it describes a symmetric predicate and its then-current corpus counts.

## Validation

Four new guidance/export cases fail against the base presentation and pass against
the corrected presentation. Synthetic detector controls retain valid rightward
second/third lines, valid single-line entries and genuine leftward findings.
The export cases exercise actual findings at three leftward positions through web
results and drilldowns, JSON, Markdown, standalone/web text, original PDFs,
highlighted PDFs and combined PDF reports. They check severity, confidence, page
references, raw details, public rule ownership and source preservation.

- Focused P018 regressions: **157 passed**.
- Report/rendering regressions: **485 passed**.
- Cross-rule regressions covering P019, P024, P054, P055, P075, P078, P087 and
  P088, plus prior P018 fixes: **313 passed**.
- Ruff: **all checks passed**. Mypy: **164 source files, no issues**.

Fresh full audits of the authorized local PDFs produce identical raw findings
before and after, including every rule's counts, details, confidence, classification,
page references and highlighting geometry:

| Document | Raw findings before → after | Visible before → after | P018 before → after |
|---|---:|---:|---:|
| Oscar | 445 → 445 | 205 → 205 | 4 → 4 |
| Praneeth | 216 → 216 | 103 → 103 | 3 → 3 |

Oscar's compliant wrapped-title target remains unflagged. Praneeth's genuine
leftward findings remain on physical pages 11–13; only their five presentation
fields (comment, correction, detailed explanation, issue label and issue help)
change. Both source PDFs retain their SHA-256 hashes. Private comparison outputs
and logs remain outside Git in the task's local notes directory.

The full nonconfidential suite is a separate final-candidate gate; the focused
counts above do not claim its completion. No reviewer-portal work, production
change, persistent-retention change, push, PR or deployment is included.
