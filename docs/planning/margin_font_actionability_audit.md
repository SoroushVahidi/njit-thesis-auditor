# Margin and Font Actionability Audit

Date: 2026-06-18

Scope:
- Active default-web PDF findings in the `margin_or_overflow` and `font_format`
  categories
- Primary rules and issue types:
  - `P011:margin_boundary_violation`
  - `P026:possible_body_font_family_issue`
  - `P026:possible_body_font_size_issue`
- Related font subcategories were checked for active default-web visibility:
  page-number font, heading font, and caption font findings are not emitted by
  the current default web audit

Decision summary:
- `P011` is a likely or confirmed layout problem, not a pure inventory signal.
  It stays visible, but every visible card must name the suspicious margin side
  when known, explain that content appears beyond the required boundary, state
  the expected NJIT margin area, and tell the student what to inspect.
- `P026` is a likely body-font problem, not a pure inventory signal. Every
  visible card must state whether the suspicion is font family or font size,
  show the observed value when available, state the expected value, and tell the
  student to confirm the flagged text role before changing styles.
- No active default-web rule checks page-number font, heading font, or caption
  font as a student-facing margin/font problem, so the UI must not imply those
  defects were detected.
- `P011` and `P026` remain highlight-only for PDF actions. If no valid bbox is
  present, the UI shows explanation-only text and no PDF-opening action.

## Rule / issue audit

| rule_id | issue_type | current title / label | current comment / explanation before fix | details fields available | observed values available | expected values available | bbox / highlight available | classification | exact wording fix needed | detector metadata insufficient? |
|---|---|---|---|---|---|---|---|---|---|---|
| P011 | `margin_boundary_violation` | `Margin boundary violation` | Generic “possible text crossing margin” wording; did not always make clear which side, what was observed, or what to inspect | `page`, `side`, `worst_overflow_pt`, `affected_line_count`, `confidence`, optional bbox/rect if synthetic/manual | Side, overflow amount, affected line count | Fixed NJIT margin area: left 1.5in; right/top/bottom 1in | Usually no in detector output; yes only when bbox/rect exists | Likely problem / Problem | Visible card must say the side when known, say content appears to cross the required boundary, state the expected NJIT margin area, list concrete things to inspect, and explicitly say when no exact highlight exists | Partial: detector identifies side and overflow, but not content type (table vs figure vs footer) |
| P026 | `possible_body_font_family_issue` | `Possible body font family issue` | Generic “font may not match requirements” wording; did not always state the observed font or expected family | `page_number`, `issue_type`, `expected`, `observed_summary`, `affected_span_count`, `candidate_count`, `confidence`, optional bbox/rect if synthetic/manual | Observed font-family summary when detector extracted one; affected span count | `Times New Roman or accepted equivalent` | Usually no in detector output; yes only when bbox/rect exists | Likely problem | Visible card must say this is a font family problem, show observed font when available, show the expected family, explain body-text intent, and tell the student to confirm the flagged text role before changing styles | Partial: no per-span role label or per-span bbox in normal detector output |
| P026 | `possible_body_font_size_issue` | `Possible body font size issue` | Generic “font size may not match requirements” wording; did not always state the observed size or expected size | `page_number`, `issue_type`, `expected`, `observed_summary`, `affected_span_count`, `candidate_count`, `confidence`, optional bbox/rect if synthetic/manual | Observed size summary when detector extracted one; affected span count | `12pt (±1pt tolerance: 11.0–13.0pt)` from detector, student-facing expectation should say `12pt` | Usually no in detector output; yes only when bbox/rect exists | Likely problem | Visible card must say this is a font size problem, show observed size when available, state the expected 12pt body-text size, and tell the student to verify whether the flagged text is body text or an allowed exception | Partial: no exact text role label or per-span bbox in normal detector output |

## Active wording policy

### Margin findings

- Visible status:
  - `Problem` when `confidence=high`
  - `Likely problem` otherwise
- Visible wording must state:
  - observed side when available (`left`, `right`, `top`, `bottom`)
  - observed condition: content appears to cross the required boundary
  - expected condition: content should stay inside NJIT's required margin area
  - concrete items to inspect: tables, figures, long lines, indentation,
    headers, footers
  - no-highlight note when no valid bbox exists:
    `No exact highlight is available for this finding.`

### Font findings

- Visible status:
  - `Problem` when `confidence=high`
  - `Likely problem` otherwise
- Visible wording must state:
  - whether the suspicion is font family or font size
  - observed value when available
  - expected value
  - that the rule is targeting body-text-like spans
  - what to check or fix:
    confirm whether the flagged text is body text, a caption, a heading, table
    text, a footnote, or another exception before changing the source style
  - no-highlight note when no valid bbox exists:
    `No exact highlight is available for this finding.`

## Visible / suppressed classification

| rule_id | issue_type | visible in main problem counts? | reason |
|---|---|---|---|
| P011 | `margin_boundary_violation` | Yes | It already encodes a specific side/boundary suspicion and can be made actionable from existing metadata |
| P026 | `possible_body_font_family_issue` | Yes | It already encodes a specific font-family suspicion and exposes observed/expected metadata |
| P026 | `possible_body_font_size_issue` | Yes | It already encodes a specific font-size suspicion and exposes observed/expected metadata |

No active default-web `P011` or `P026` issue type is treated as pure inventory
after this audit. If a future detector adds a margin/font signal that cannot say
what is suspicious, it should be moved to a review-signal or developer-only
surface rather than counted as a student-facing problem.

## Remaining limitations

- `P011` does not identify whether the offending content is specifically a table,
  figure, footer, header, long line, or paragraph text. The UI can only name the
  suspicious side and direct the student to inspect likely causes.
- `P026` does not emit per-span highlights in normal detector output, so most
  font findings remain explanation-only with no PDF action.
- `P026` does not emit an exact semantic text role label in normal detector
  output; the UI must describe the finding as applying to body-text-like spans
  and ask the student to confirm whether the flagged text is really body text.
- No active default-web rule currently checks student-facing font family or font
  size compliance for page numbers, captions, or headings in the same actionability
  surface.

## Validation target

- `ruff check .`
- `mypy src`
- `python -m pytest`

## Validation results

- `ruff check .` — passed
- `mypy src` — passed
- `python -m pytest` — passed (`1545 passed, 1 warning`)
