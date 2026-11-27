"""Direct sample audits use the same private, temporary PDF jobs as uploads."""

from __future__ import annotations

import hashlib
import importlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from njit_auditor.synthetic_sample import sample_pdf
from njit_auditor.web_samples import get_builtin_sample

SAMPLE_IDS = ["synthetic_example", *(f"ester_sample_{letter}" for letter in "abcd")]


@pytest.fixture()
def site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(tmp_path / "jobs"))
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(tmp_path / "feedback.sqlite3"))
    import njit_auditor.web_app as web

    importlib.reload(web)
    with TestClient(web.app, follow_redirects=False) as client:
        yield client, web


def _job_id(response) -> str:
    assert response.status_code == 303
    path = urlsplit(response.headers["location"]).path
    assert path.startswith("/audits/")
    return path.rsplit("/", 1)[-1]


def test_sample_form_is_native_and_keeps_upload_and_downloads(site) -> None:
    client, _ = site
    page = client.get("/")
    assert page.status_code == 200
    assert 'action="/sample-audits"' in page.text
    assert "Audit a Sample Document" in page.text
    assert "Audit Selected Sample" in page.text
    for sample_id in SAMPLE_IDS:
        assert f'value="{sample_id}"' in page.text
    assert 'action="/audits"' in page.text
    assert 'type="file"' in page.text
    assert 'href="/sample.pdf"' in page.text
    assert 'href="/samples/ester_sample_a.pdf"' in page.text


@pytest.mark.parametrize("sample_id", SAMPLE_IDS)
def test_direct_sample_creates_ordinary_isolated_pdf_job(site, sample_id: str) -> None:
    client, web = site
    if sample_id != "synthetic_example" and not get_builtin_sample(sample_id).abs_path.is_file():
        pytest.skip("Historical PDF is unavailable in this checkout")
    with patch.object(web, "_run_audit_task", lambda job_id: None):
        response = client.post("/sample-audits", data={"sample_id": sample_id})
    job_id = _job_id(response)
    job = web._get_job(job_id)
    assert job is not None and job.state == "pending"
    stored = web._job_pdf_path(web._job_dir(job_id)).read_bytes()
    expected = (sample_pdf() if sample_id == "synthetic_example" else
                get_builtin_sample(sample_id).abs_path.read_bytes())
    assert hashlib.sha256(stored).digest() == hashlib.sha256(expected).digest()
    assert client.get(f"/audits/{job_id}").status_code == 200


@pytest.mark.parametrize("fields", [
    {}, {"sample_id": "unknown"}, {"sample_id": "../private.pdf"},
    {"sample_id": "https://example.invalid/private.pdf"},
    {"sample_id": "ester_sample_a", "pdf_url": "https://example.invalid/file.pdf"},
])
def test_invalid_sample_request_creates_no_job(site, fields: dict[str, str]) -> None:
    client, web = site
    response = client.post("/sample-audits", data=fields)
    assert response.status_code in {303, 400}
    if response.status_code == 303:
        assert response.headers["location"].startswith("/?error=")
    assert not web._jobs
    assert not web.RUNTIME_DIR.exists() or not list(web.RUNTIME_DIR.iterdir())


def test_duplicate_sample_ids_are_rejected(site) -> None:
    client, web = site
    response = client.post(
        "/sample-audits",
        content="sample_id=synthetic_example&sample_id=ester_sample_a",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code in {303, 400}
    if response.status_code == 303:
        assert response.headers["location"].startswith("/?error=")
    assert not web._jobs


@pytest.mark.parametrize("sample_id", ["synthetic_example", "ester_sample_a"])
def test_sample_respects_upload_size_limit(site, monkeypatch: pytest.MonkeyPatch,
                                           sample_id: str) -> None:
    client, web = site
    if sample_id != "synthetic_example" and not get_builtin_sample(sample_id).abs_path.is_file():
        pytest.skip("Historical PDF is unavailable in this checkout")
    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 100)
    response = client.post("/sample-audits", data={"sample_id": sample_id})
    assert response.headers["location"].startswith("/?error=")
    assert not web._jobs
    assert not web.RUNTIME_DIR.exists() or not list(web.RUNTIME_DIR.iterdir())


@pytest.mark.parametrize("damage", ["missing", "modified"])
def test_missing_or_modified_historical_sample_is_rejected(
    site, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    import njit_auditor.web_samples as samples

    client, web = site
    relative = "data/raw/ester/approved.pdf"
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    original = b"%PDF-1.4\nApproved synthetic test bytes\n%%EOF\n"
    source.write_bytes(original)
    monkeypatch.setattr(samples, "_REPO_ROOT", tmp_path)
    monkeypatch.setitem(samples._BY_ID, "ester_sample_a", samples.SampleInfo(
        "ester_sample_a", "Test sample", relative,
    ))
    monkeypatch.setitem(samples._PUBLIC_SAMPLE_SHA256, "ester_sample_a",
                        hashlib.sha256(original).hexdigest())
    if damage == "missing":
        source.unlink()
    else:
        source.write_bytes(b"%PDF-1.4\nChanged bytes\n%%EOF\n")
    response = client.post("/sample-audits", data={"sample_id": "ester_sample_a"})
    assert response.headers["location"].startswith("/?error=")
    assert not web._jobs
    assert not web.RUNTIME_DIR.exists() or not list(web.RUNTIME_DIR.iterdir())


def test_sample_registry_cannot_read_file_outside_repository(
    site, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import njit_auditor.web_samples as samples

    client, web = site
    repo = tmp_path / "repo"
    repo.mkdir()
    unrelated = tmp_path / "unrelated.pdf"
    content = b"%PDF-1.4\nUnrelated synthetic test bytes\n%%EOF\n"
    unrelated.write_bytes(content)
    monkeypatch.setattr(samples, "_REPO_ROOT", repo)
    monkeypatch.setitem(samples._BY_ID, "ester_sample_a", samples.SampleInfo(
        "ester_sample_a", "Test sample", "../unrelated.pdf",
    ))
    monkeypatch.setitem(samples._PUBLIC_SAMPLE_SHA256, "ester_sample_a",
                        hashlib.sha256(content).hexdigest())
    response = client.post("/sample-audits", data={"sample_id": "ester_sample_a"})
    assert response.headers["location"].startswith("/?error=")
    assert not web._jobs
    assert unrelated.read_bytes() == content


def test_concurrent_guest_sample_audits_get_separate_jobs_and_expire(site) -> None:
    client, web = site
    with patch.object(web, "_run_audit_task", lambda job_id: None):
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(
                lambda _: client.post("/sample-audits", data={"sample_id": "synthetic_example"}),
                range(2),
            ))
    job_ids = [_job_id(response) for response in responses]
    assert len(set(job_ids)) == 2
    assert all(web._job_pdf_path(web._job_dir(job_id)).read_bytes() == sample_pdf()
               for job_id in job_ids)
    for job_id in job_ids:
        job = web._get_job(job_id)
        assert job is not None
        job.state = "complete"
        job.created_at = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        job.finished_at = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        web._set_job(job)
    assert web.cleanup_expired_jobs() >= 2
    assert all(not web._job_dir(job_id).exists() for job_id in job_ids)


def test_normal_pdf_upload_still_uses_same_job_path(site) -> None:
    client, web = site
    with patch.object(web, "_run_audit_task", lambda job_id: None):
        response = client.post("/audits", files={
            "file": ("own-thesis.pdf", sample_pdf(), "application/pdf"),
        })
    job_id = _job_id(response)
    assert web._job_pdf_path(web._job_dir(job_id)).read_bytes() == sample_pdf()
    assert web._get_job(job_id).file_name == "own-thesis.pdf"


@pytest.mark.parametrize("sample_id", SAMPLE_IDS)
def test_direct_audit_matches_manual_pdf_upload_results(site, sample_id: str) -> None:
    client, web = site
    if sample_id == "synthetic_example":
        source = sample_pdf()
        name = "synthetic-example.pdf"
    else:
        from njit_auditor.web_samples import get_public_sample

        if not get_builtin_sample(sample_id).abs_path.is_file():
            pytest.skip("Historical PDF is unavailable in this checkout")
        sample = get_public_sample(sample_id)
        source = sample.abs_path.read_bytes()
        name = sample.abs_path.name

    with patch.object(web, "_run_audit_task", lambda job_id: None):
        direct = client.post("/sample-audits", data={"sample_id": sample_id})
        manual = client.post("/audits", files={
            "file": (name, source, "application/pdf"),
        })
    direct_id, manual_id = _job_id(direct), _job_id(manual)
    for job_id in (direct_id, manual_id):
        web._execute_audit_task(job_id)
    direct_job, manual_job = web._get_job(direct_id), web._get_job(manual_id)
    assert direct_job is not None and manual_job is not None
    assert direct_job.state == manual_job.state == "complete"
    assert direct_job.audit_type == manual_job.audit_type == "pdf"
    assert direct_job.finding_count == manual_job.finding_count
    assert direct_job.fail_count == manual_job.fail_count
    assert direct_job.warn_count == manual_job.warn_count
    assert direct_job.failed_check_count == manual_job.failed_check_count
    assert direct_job.findings == manual_job.findings
    assert client.get(f"/audits/{direct_id}").status_code == 200
