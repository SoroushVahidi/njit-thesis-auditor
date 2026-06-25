# Open PR Triage (2026-06-25)

Short status note for open pull requests that must **not** be closed, merged, or
rebased as part of routine repository cleanup unless explicitly requested.

| PR | Branch | Status | Maintainer note |
|---|---|---|---|
| [#311](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/311) | `feature/subpage-location-labels` | **Open** | Older sub-page location-label work. Superseded in spirit by the geometry-driven `sub_page_location_label()` / `enriched_pdf_location_label()` chain on current `main`, but **do not touch** until separately reviewed. |
| [#349](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/349) | `docs/protect-autonomous-policy-and-ester-status` | **Open** | Autonomous-agent policy and Ester feedback audit docs. **Do not touch** until separately reviewed. |
| [#362](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/362) | `ux/review-needed-prefix-policy` | **Open** | Review-needed prefix policy clarification. Needs a separate review decision before merge or close. |

## Cleanup guardrails

- Do **not** close, merge, rebase, or delete these PRs during hygiene passes.
- Do **not** delete their head branches without an explicit decision.
- For broader triage history, see also `docs/status/pr_and_stash_triage_20260619.md`.
