# PR #505 reduction after PR #508 (2026-07-14)

Privacy-safe reconstruction report for reducing open PR #505 onto current
`origin/main` after #508 merged.

## Baseline

| Field | Value |
|---|---|
| `origin/main` | `e75d5b8dc5e2125e04743bacc42459252f2f65a9` (#508 squash) |
| Old #505 head | `e772f5fd81beb138ec4d1413e9fc2593e12823e1` |
| Reconstruction branch | `fix/reduce-pr-505-after-508` |
| Worktree | `njit-thesis-auditor-clean-worktrees/reduce-pr-505-20260714` |
| Method | Cherry-pick unique commits; drop superseded hunks; no wholesale rebase |
| Live server / port 8000 | Untouched |

Machine-readable overlap inventory:
`results/pr505_reconstruction_overlap.json` (ignored `/results/` path; also
summarized below).

## Baseline validation (before reconstruction)

Measured on a clean worktree at `e75d5b8`:

| Check | Result |
|---|---|
| `ruff check .` | passed |
| `mypy src` | passed (107 source files) |
| `python -m pytest -q tests` | **2775 passed** (environment-collected count; #508 docs had cited 2755/2) |

## Workstream classification

| Workstream | Classification | Action |
|---|---|---|
| P015 continuation-line indentation (`df71d7c`, `e772f5f`) | **retained** | Detector + synthetic tests + student-facing wording for `unexpected_indent_on_continuation_line` |
| P011 content-aware remediation (`822ad2e`) | **retained** | Presentation/remediation wording only |
| P011 precision regression tests/docs (`5eb0bfb`) | **retained** | Near-miss / bottom-margin / highlight geometry tests; inventory writes under `results/` |
| P033 Title Page role wording (`a9efeff`) | **retained** | `title_page` key + grammatical "other front-matter page" fallback |
| Duplicate-candidate diagnostic tooling (`a9efeff`) | **retained** | Offline only; human-review CLI; optional JSON under `results/` |
| P026 Approval Page font concatenated-heading (`5ba3acc`) | **already on main** | Empty vs main after #506; dropped |
| Generic polished-comment rule-ID leak (`ab2c2c3`) | **superseded** | #508 already fixed/expanded; dropped |
| Overnight status docs (`9f6d4f8` + status hunks in `e772f5f`) | **obsolete** | Superseded by #508 canonical status/docs; not reintroduced |
| Private forensics metadata/quotes from #504 | **rejected** | Replaced with privacy-safe summary only |
| P011 footer-zone / non-text margin policy | **deferred** | Esther judgment required; no detector/threshold changes |

## Intentionally not reintroduced

- #505 wording change from "This automated check" → "This formatting check"
  (main/#508 keeps "automated check" with stronger leak tests).
- Stale `overnight_esther_correctness_20260712.md` / giant status edits with old SHAs.
- Byte-identical P026 font hunk.
- Private PDF filenames, personal names, annotation text, dissertation quotes.

## Deferred Esther-policy questions

- Footer-zone body-text P011 policy (Sample A cluster).
- Non-text image/drawing margin coverage for P011.
- Remaining unreviewed medium-confidence P011 pages on Sample B.
- Whether any duplicate-warning candidates should ever auto-suppress (tool remains diagnostic-only).

## Privacy protections in this reduction

- Forensics doc rewritten without private filenames/names/quotes.
- Absolute host paths removed from retained P011 audit doc.
- Diagnostic scripts default writes under ignored `results/`.
- Duplicate CLI hashes paths into `sample-<digest>` IDs for JSON.
- No private dissertation content, student names, or extracted body text in this report.
