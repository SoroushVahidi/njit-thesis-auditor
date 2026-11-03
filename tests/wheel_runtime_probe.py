"""Exercise runtime resources and synthetic exports in a separate interpreter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.source:
        sys.path.insert(0, str(args.source / "src"))
    work = args.output.parent / "runtime"
    work.mkdir(exist_ok=True)
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(work / "jobs")

    def deny_connect(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Runtime resource loading must not connect to a network")

    socket.socket.connect = deny_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = deny_connect  # type: ignore[assignment,method-assign]
    import pymupdf
    from fastapi.testclient import TestClient
    from reportlab import rl_config

    import njit_auditor
    import njit_auditor.report_outputs as outputs
    import njit_auditor.report_text as text
    import njit_auditor.web_app as web
    from njit_auditor.audit_runner import run_pdf_audit_full
    from njit_auditor.ester_warning_wording import _load_map
    from njit_auditor.polished_comments import _remediation_by_rule
    from njit_auditor.report_view import build_report_view
    from njit_auditor.specs.q_rule_coverage import build_coverage_report
    from njit_auditor.student_pdf_report import (
        build_combined_student_pdf_report,
        render_student_report_text,
    )

    if not args.source:
        assert Path(njit_auditor.__file__).resolve().is_relative_to(Path(sys.prefix))
        assert sys.prefix != sys.base_prefix
        assert not sys.flags.no_site
        assert sys.flags.isolated

    # Control volatile metadata before generation; compare bytes without normalization.
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return datetime(2026, 1, 1, tzinfo=timezone.utc)

    outputs.datetime = FixedDatetime
    text.datetime = FixedDatetime
    rl_config.invariant = 1
    original_save = pymupdf.Document.save

    def stable_save(self: object, *save_args: object, **kwargs: object) -> object:
        kwargs["no_new_id"] = True
        return original_save(self, *save_args, **kwargs)

    pymupdf.Document.save = stable_save

    catalog = web._build_rule_catalog()
    assert any(rule["id"] == "P013" for rule in catalog["student_rules"])
    assert _load_map()["rules"]
    assert _remediation_by_rule()
    assert text._full_remediation_by_rule()
    snapshot: dict[str, object] = {
        "catalog": digest(catalog),
        "wording": digest(_load_map()),
        "short_remediation": digest(_remediation_by_rule()),
        "full_remediation": digest(text._full_remediation_by_rule()),
        "coverage": digest([asdict(row) for row in build_coverage_report()]),
    }
    for template in (
        "_macros.html", "base.html", "help.html", "index.html",
        "job.html", "problem_group.html", "rules.html",
    ):
        web._templates.get_template(template)
    with TestClient(web.app) as client:
        for route in ("/", "/help", "/rules"):
            response = client.get(route)
            assert response.status_code == 200
            if route != "/":  # Optional private source samples are deliberately not distributed.
                snapshot[route] = hashlib.sha256(response.content).hexdigest()
        assert 'id="P013"' in client.get("/rules").text

    for name, rotation in (("normal", 0), ("rotated", 90)):
        source = work / f"{name}.pdf"
        with pymupdf.open() as document:
            page = document.new_page(width=612, height=792)
            page.insert_text((30, 72), "Synthetic formatting audit example.")
            page.set_rotation(rotation)
            document.save(source)
        findings = run_pdf_audit_full(source)
        assert findings
        metadata = {"audit_type": "pdf", "input_file_name": source.name,
                    "generated_at": "2026-01-01T00:00:00+00:00"}
        payload = outputs.audit_findings_to_json_dict(findings, metadata)
        view = build_report_view(payload)
        visible = [asdict(finding) for finding in view.findings]
        outputs.write_json_report(findings, metadata, work / "report.json")
        outputs.write_markdown_report(findings, metadata, work / "report.md")
        text.write_text_report(findings, metadata, work / "report.txt")
        (work / "student.txt").write_text(
            render_student_report_text(visible, file_name=source.name), encoding="utf-8",
        )
        build_combined_student_pdf_report(
            source, work / "combined.pdf", visible, boxes_by_problem={}, file_name=source.name,
        )
        snapshot[name] = {
            "findings": digest([finding.model_dump(mode="json") for finding in findings]),
            "view": digest(visible),
            "exports": {ext: hashlib.sha256((work / ext).read_bytes()).hexdigest()
                        for ext in ("report.json", "report.md", "report.txt",
                                    "student.txt", "combined.pdf")},
        }
    args.output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
