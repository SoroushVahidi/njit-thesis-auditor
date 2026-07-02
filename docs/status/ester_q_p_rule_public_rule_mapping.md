# Ester Q-Rule → P-Rule → Public Rule Card Mapping

> **Purpose:** Reduce confusion between Ester's YES/NO audit questions (Q-rules), backend
> detector catalog entries (P-rules), and student-facing `/rules` cards.
>
> **Canonical live status:** [current_project_state_and_next_steps.md](current_project_state_and_next_steps.md)

## Three layers (read top to bottom)

| Layer | Canonical file / code | Audience | What it represents |
|---|---|---|---|
| **Ester Q-rule** | `data/specs/ester_q_matrix.json` | Maintainers, coverage audits | Atomic YES/NO questions from Ester's audit logic matrix (Q001–Q079): `question`, `rule_definition`, `remediation`, `automatable` |
| **Backend P-rule** | `data/processed/rules/project_added_rules.json` | Detectors, tests, CLI | Project-added detector catalog (P001–P083): `question`, `rule_definition`, `remediation`, `notes`, `q_rule_ids` — one P-rule may reference many Q-rules |
| **Public rule card** | Built at runtime by `_build_rule_catalog()` in `src/njit_auditor/web_app.py` | Students (`GET /rules`) | Student-friendly card per P-rule: title, "What it checks", "How to correct it" — sourced from the P-rule catalog with `_RULE_TEXT_OVERRIDES` / `_websafe_rule_text()` sanitization |

**Finding flow:** PDF detectors emit findings tagged with **`rule_id` (P-rule)** and often **`source_q_rule` / issue metadata** in `details`. Audit results link to `/rules#P0xx`. Confidence badges apply to **findings**, not to static rule cards.

## Supporting spec artifacts

| File | Role |
|---|---|
| `data/specs/ester_p_rule_feedback.json` | Ester's proposed edits to a **subset** of P-rules (19 rules with feedback); informs wording alignment — not the runtime detector source |
| `data/specs/q_rule_coverage_report.json` | Generated Q001–Q079 → implementing P-rules map; summary counts as of file `generated` date |
| `data/processed/rules/njit_rule_inventory.json` | Legacy Q001–Q079 inventory used by early tests; **do not edit** `implementation_status` casually — see [stale_docs_cleanup_20260619.md](stale_docs_cleanup_20260619.md) |
| `src/njit_auditor/specs/q_rule_coverage.py` | Code that rebuilds coverage from `ester_q_matrix.json` + `project_added_rules.json` |

## Coverage snapshot (`main` @ `cdc99ea`)

From `data/specs/q_rule_coverage_report.json` (generated 2026-06-30):

| Status | Count | Meaning |
|---|---:|---|
| `implemented` | 67 | At least one P-rule maps to the Q-rule |
| `manual_review_only` | 12 | `automatable: false` in Q-matrix (template/NLP/manual) |
| `unimplemented` | 0 | Automatable Q-rules with no P-rule mapping |

Open PR [#388](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/388) proposes a **`partial`** tier (detector notes explicitly exclude the check). That tier is **not on `main` yet**.

## Example mappings (illustrative)

| Ester Q | P-rule(s) | Public card | Notes |
|---|---|---|---|
| Q002, Q003 | P015, P044 | `/rules#P015`, `/rules#P044` | Abstract indentation split across general body indent (P015) and Abstract-only (P044) |
| Q004, Q005 | P078 | `/rules#P078` | Abstract forbidden terms / pronouns |
| Q006 | P074 | `/rules#P074` | Title page graduation month |
| Q049–Q051 (TOC terminal period) | P054 | `/rules#P054` | TOC-side punctuation |
| Q056, Q057 | P018, P039, P060, … | `/rules#P018` | Multiple P-rules; P018 is the broad TOC/list alignment detector |

Many Q-rules map to **multiple** P-rules (front-matter headings, TOC/list family). Conversely, one P-rule often lists **many** Q-IDs in `notes` / `q_rule_ids` even when only some checks are fully automated — see coverage report `implementing_p_rules` per Q-row.

## Ester alignment work in flight

Recent merges ([#381](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/381)–[#387](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/387)) ingested spreadsheet specs and aligned catalog wording. Stacked PRs **#394 → #395 → #396** further split P026 / P015 / P018 public rule references per Ester guidance — see [open_pr_triage.md](open_pr_triage.md).

## Maintainer rules

- **Do not** change rule IDs, detector thresholds, or canonical JSON spec contents during doc-only cleanup.
- **Do not** start **P084** unless explicitly instructed.
- Regenerate `q_rule_coverage_report.json` only via the project's coverage tooling/tests — not by hand-editing counts in docs.
- Keep student-facing `/rules` language free of internal jargon ("heuristic", "P-rule", agent policy terms) — overrides live in `web_app.py`, not in committed private samples.
