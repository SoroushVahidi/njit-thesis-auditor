# Private reviewer judgment replay

`scripts/ester_judgment_replay.py` runs the same web upload path that creates
student cards and checks a private case manifest. The manifest and PDF sources
must stay outside Git. Run from a clean checkout of the candidate SHA:

```bash
PYTHONPATH=src python scripts/ester_judgment_replay.py \
  --manifest /private/ester_replay_manifest.json \
  --output-dir /private/replay-candidate \
  --baseline-dir /private/replay-baseline \
  --liveness /private/rule_liveness_counts.json
```

The output directory contains per-document web results and
`judgment_results.json`. `--cached` checks saved results without rerunning PDFs.
The runner verifies each document's SHA-256 before a fresh replay and rejects
incomplete audits. It requires exactly 111 false-positive, 20 true-positive,
and five additional reviewer-violation cases, with unique IDs.

Each case preserves its original source, date, rule, current owner, and
judgment. A `target` selector requires a rule, physical PDF page, and issue
type. It can also specify a target box and detail predicates such as entry
index or margin side. True positives must have a matching raw finding and a
student card linked to that raw finding's audit index; cases requiring a
highlight verify its target. A reviewer violation
covering several lines can list `required_highlight_targets` so one nearby
highlight cannot satisfy it. False positives require the rejected target's
absence. `disposition` records whether an FP was resolved, disabled, or
retired. Detector liveness counts are required for rules labeled resolved.

With `--baseline-dir`, the gate also reports any disappearing student finding
outside the manifest's explicit `allowed_removed` list. It preserves raw issue
identity and matches duplicate findings one-to-one. Review those removals
before accepting a detector change. Cases with `verification_level=claim_page`
use a conservative page-and-claim absence guard where original coordinates
were not preserved; `verification_level=target` has a coordinate or detail
anchor. This distinction must remain visible in the private manifest and
the final evidence report. The 82 historical false positives without original
coordinates establish page/claim absence only, not exact geometric absence.

Use synthetic PDF tests in CI for the corrected detector paths. The private
manifest and original PDFs are needed for the complete historical replay.
