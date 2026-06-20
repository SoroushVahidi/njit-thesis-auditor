# Stale Docs Cleanup — 2026-06-19

**Branch:** `fix/stale-docs-and-pr305-cleanup`  
**Baseline:** `main` @ `5434665d7aafa94e7ba00fd5ea9ec77e3389e2bf`  
**Scope:** Documentation and PR #305 resolution only. No detector, threshold, rule-ID, or UI-behavior changes.

---

## 1. Summary

Stale planning/status artifacts were marked historical or corrected so future agents
do not treat pre-#321 `"Open PDF page"` action patterns as current. PR #305 was
closed as superseded because its example-URL UI already exists on current `main`.

---

## 2. Documents inspected

| Document | Action | Rationale |
|---|---|---|
| `docs/planning/finding_actionability_matrix.md` | **Updated** — historical banner + **Current policy** section | Matrix table is useful history but contradicted live UI (page-only labels, no problem numbers). Banner + current-policy block added; table left intact under historical heading. |
| `data/processed/rules/njit_rule_inventory.json` | **Left untouched** | Canonical Q-rule inventory (Q001–Q079) consumed by `tests/test_rule_inventory.py` and evaluation manifest. `implementation_status` / `implementation_module` fields are stale tracking snapshots (last meaningfully refreshed ~2026-06-08) but editing them would change canonical rule JSON semantics. Stale status documented here instead. |
| `docs/web_ui_manual_qa_checklist.md` | **Updated** — fixed action-label contradictions; documented example URL box | Directly contradicted current `"Read explanation"` label and omitted PR #305-equivalent example URL helper already on `main`. |
| `docs/web_ui_demo_guide.md` | **No change** | Step 3 already documents the built-in example URL helper on current `main`. |
| `docs/planning/bespoke_long_tail_remediation_audit.md` | **Referenced** | Prior pass noted these stale artifacts; this cleanup completes that follow-up. |

---

## 3. `njit_rule_inventory.json` — why not regenerated

- **Role:** Authoritative Q-rule question/remediation inventory (79 rows), not a generated runtime artifact.
- **Tests:** `test_all_ester_rules_represented_in_inventory`, manifest validation, and multiple planning docs depend on stable Q IDs and field shapes.
- **Stale fields:** `implementation_status` and `implementation_module` undercount current P-rule coverage (e.g. LoT/LoF family listed as unimplemented while P031–P061 detectors exist). Regenerating without a dedicated, reviewed inventory workflow risks silent semantic drift.
- **Safe action:** Treat `implementation_status` as **historical tracking** until a future controlled inventory refresh task explicitly updates it with test-backed regeneration.

For current P-rule coverage, prefer `project_added_rules.json`, detector source, and evaluation docs over `implementation_status` in the Q inventory.

---

## 4. Current behavior summary (authoritative)

- Every visible finding has a stable **problem number**.
- **Open highlighted PDF page** — real drawable highlight only.
- **Open original PDF page** — page known, no highlight.
- **Read explanation** — document-level / no page.
- Forbidden labels: `"Open PDF"`, `"Open PDF page"`, `"Open first example page"`.
- Upload page includes **Try an example** Digital Commons URL helper (`#example-thesis-box`).

---

## 5. PR #305 resolution

| Item | Finding |
|---|---|
| Original PR | [#305](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/305) — example NJIT thesis URL on upload page |
| Diff vs current `main` | UI feature **already present** on `main` (landed via #306 and follow-on upload-page work); tests in `tests/test_web_app.py` already cover `#example-thesis-box` and `#fill-example-url`. |
| Conflicts | PR branch predates problem numbering, strict highlight policy, and expanded `test_web_app.py`; rebasing would mostly conflict in tests/docs for no new UI delta. |
| **Chosen path** | **Close as superseded** — no duplicate reimplementation. Comment added pointing to current `main` and this cleanup PR. |

---

## 6. Validation

Run on branch before merge:

```bash
ruff check .
mypy src
python -m pytest -q
```

New tests: `tests/test_stale_docs_cleanup.py`.

---

## 7. Recommended next action

Inspect the old stash on a throwaway branch and salvage only still-useful no-raw-LaTeX tests, or continue reducing the remaining 36 generic remediation `(rule_id, issue_type)` pairs documented in `docs/planning/bespoke_long_tail_remediation_audit.md`.
