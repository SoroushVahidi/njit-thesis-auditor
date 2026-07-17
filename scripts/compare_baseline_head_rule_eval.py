#!/usr/bin/env python3
"""Compare a rule's findings between two worktrees with anti-swap safeguards.

This helper exists because a prior P051 packaging narrative briefly inverted the
broader-archive counts (reporting baseline/head as 3/10 instead of 10/3). The
self-checks below make silent label swaps fail loudly.

Each arm is evaluated in a fresh subprocess with that worktree's ``src/`` on
``PYTHONPATH``, so baseline/head code cannot be mixed in one interpreter.

Example:
  python scripts/compare_baseline_head_rule_eval.py \\
    --rule-id P051 \\
    --baseline-worktree /tmp/njit-p051-origin-main \\
    --head-worktree /tmp/njit-p051-copyright-year \\
    --pdf-dir /path/to/corpus \\
    --out /tmp/p051_compare.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_WORKER = r"""
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from njit_auditor.audit_runner import run_pdf_audit_full

role, worktree, rule_id, out_path = sys.argv[1:5]
pdfs = [Path(p) for p in sys.argv[5:]]
sha = subprocess.check_output(
    ["git", "-C", worktree, "rev-parse", "HEAD"], text=True
).strip()
rule_counts: Counter[str] = Counter()
cases = []
hashes = {}
signatures = {}
for pdf in pdfs:
    hashes[pdf.name] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    findings = run_pdf_audit_full(pdf)
    rule_counts.update(f.rule_id for f in findings)
    signatures[pdf.name] = sorted(
        [
            [
                f.rule_id,
                (f.details or {}).get("issue_type") or "",
                f.page if f.page is not None else -1,
            ]
            for f in findings
        ],
        key=lambda item: (item[0], item[1], item[2]),
    )
    for finding in findings:
        if finding.rule_id != rule_id:
            continue
        details = finding.details or {}
        cases.append(
            {
                "pdf": pdf.name,
                "page": finding.page,
                "issue_type": details.get("issue_type"),
                "confidence": details.get("confidence"),
                "year_association": details.get("year_association"),
                "copyright_marker_detected": details.get("copyright_marker_detected"),
            }
        )
payload = {
    "role": role,
    "worktree": str(Path(worktree).resolve()),
    "sha": sha,
    "pdf_hashes": hashes,
    "rule_counts": dict(sorted(rule_counts.items())),
    "target_rule_count": rule_counts.get(rule_id, 0),
    "target_rule_cases": cases,
    "signatures_by_pdf": signatures,
}
Path(out_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
"""


def _git_sha(worktree: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def _run_side(
    *,
    role: str,
    worktree: Path,
    pdfs: list[Path],
    rule_id: str,
    out_path: Path,
) -> dict[str, Any]:
    src_root = worktree / "src"
    if not src_root.is_dir():
        raise SystemExit(f"{role} worktree missing src/: {worktree}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_root)
    cmd = [
        sys.executable,
        "-c",
        _WORKER,
        role,
        str(worktree),
        rule_id,
        str(out_path),
        *[str(pdf) for pdf in pdfs],
    ]
    subprocess.run(cmd, check=True, env=env)
    return json.loads(out_path.read_text())


def _assert_no_label_swap(baseline: dict[str, Any], head: dict[str, Any]) -> None:
    if baseline["role"] != "baseline":
        raise SystemExit(f"baseline role must be 'baseline', got {baseline['role']!r}")
    if head["role"] != "head":
        raise SystemExit(f"head role must be 'head', got {head['role']!r}")
    if baseline["sha"] == head["sha"]:
        raise SystemExit(
            "baseline and head resolve to the same SHA; refusing comparison "
            f"({baseline['sha']})"
        )
    if baseline["worktree"] == head["worktree"]:
        raise SystemExit(
            "baseline and head use the same worktree path; refusing comparison"
        )
    if baseline["pdf_hashes"] != head["pdf_hashes"]:
        raise SystemExit(
            "PDF bytes differ between baseline and head arms; refusing comparison. "
            "Re-run with an explicit shared --pdf-dir corpus."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--rule-id", required=True, help="Rule ID to summarize, e.g. P051")
    parser.add_argument("--baseline-worktree", type=Path, required=True)
    parser.add_argument("--head-worktree", type=Path, required=True)
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        required=True,
        help="Directory of PDF files used for BOTH arms (shared corpus).",
    )
    parser.add_argument(
        "--pdf-glob",
        default="*.pdf",
        help="Glob under --pdf-dir (default: *.pdf)",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    pdfs = sorted(args.pdf_dir.glob(args.pdf_glob))
    if not pdfs:
        raise SystemExit(f"No PDFs matched {args.pdf_dir}/{args.pdf_glob}")

    # Preflight SHAs so a same-SHA mistake fails before long audits.
    baseline_sha = _git_sha(args.baseline_worktree)
    head_sha = _git_sha(args.head_worktree)
    if baseline_sha == head_sha:
        raise SystemExit(
            f"baseline and head resolve to the same SHA ({baseline_sha}); refusing"
        )

    with tempfile.TemporaryDirectory(prefix="njit_rule_eval_") as tmp:
        tmp_path = Path(tmp)
        baseline = _run_side(
            role="baseline",
            worktree=args.baseline_worktree,
            pdfs=pdfs,
            rule_id=args.rule_id,
            out_path=tmp_path / "baseline.json",
        )
        head = _run_side(
            role="head",
            worktree=args.head_worktree,
            pdfs=pdfs,
            rule_id=args.rule_id,
            out_path=tmp_path / "head.json",
        )

    _assert_no_label_swap(baseline, head)

    report = {
        "rule_id": args.rule_id,
        "pdf_dir": str(args.pdf_dir.resolve()),
        "pdf_count": len(pdfs),
        "baseline": baseline,
        "head": head,
        "delta_target_rule_count": head["target_rule_count"]
        - baseline["target_rule_count"],
        "self_check": {
            "baseline_role": baseline["role"],
            "head_role": head["role"],
            "baseline_sha": baseline["sha"],
            "head_sha": head["sha"],
            "shared_pdf_hashes": True,
            "roles_not_swapped": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        f"{args.rule_id}: baseline({baseline['sha'][:12]})="
        f"{baseline['target_rule_count']} "
        f"head({head['sha'][:12]})={head['target_rule_count']} "
        f"delta={report['delta_target_rule_count']}"
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
