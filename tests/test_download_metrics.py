"""Synthetic tests for private Windows installer counter observations."""

from __future__ import annotations

import io
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Barrier
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request

import pytest

from njit_auditor.analytics import downloads
from njit_auditor.analytics.downloads import ApprovedInstaller, capture, initialize, report

_DIGEST = "sha256:" + "1" * 64
_INSTALLER = ApprovedInstaller(14, 91, "3.2.1-rc.4", 1200, _DIGEST)
_CANARY = "UNUSED-PROVIDER-PERSONAL-DETAIL"


def _at(day: int, minute: int = 0) -> datetime:
    return datetime(2030, 4, day, 0, minute, tzinfo=timezone.utc)


def _metadata(
    count: int, installer: ApprovedInstaller = _INSTALLER, *, digest: str = _DIGEST,
) -> dict:
    return {
        "id": installer.release_id,
        "tag_name": installer.tag,
        "draft": False,
        "prerelease": True,
        "published_at": "2030-03-30T21:00:00Z",
        "author": {"login": _CANARY},
        "assets": [{
            "id": installer.asset_id,
            "name": installer.filename,
            "size": installer.size,
            "digest": digest,
            "state": "uploaded",
            "download_count": count,
            "created_at": "2030-03-30T20:00:00Z",
            "browser_download_url": (
                "https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/download/"
                f"{installer.tag}/{installer.filename}"
            ),
            "uploader": {"login": _CANARY},
        }],
    }


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    state = tmp_path / "private"
    state.mkdir(mode=0o700)
    path = state / "downloads.sqlite"
    initialize(path)
    return path


def _capture(
    path: Path, day: int, count: int, *, minute: int = 0,
    installer: ApprovedInstaller = _INSTALLER, digest: str = _DIGEST,
):
    return capture(
        path, installer, _at(day).date(),
        fetch=lambda release_id: _metadata(count, installer, digest=digest),
        clock=lambda: _at(day, minute),
    )


def test_observed_counts_dates_and_privacy(db_path):
    for day, count in ((1, 100), (2, 103), (3, 103), (4, 106)):
        _capture(db_path, day, count)
    raw = db_path.read_bytes()
    result = report(db_path, _INSTALLER, _at(1), _at(4))
    assert result["coverage"] == "complete"
    assert result["exact_counter_delta"] == result["lower_bound"] == result["upper_bound"] == 6
    assert [item["counter_delta"] for item in result["intervals"]] == [3, 0, 3]
    assert result["latest_provider_observation"]["provider_count"] == 106
    assert result["latest_provider_observation"]["observed_at_utc"] == _at(4).isoformat()
    assert result["gaps"] == []
    assert result["observations"][0]["asset_digest"] == _DIGEST
    assert _CANARY.encode() not in raw
    assert _CANARY not in json.dumps(result)
    assert db_path.read_bytes() == raw
    assert db_path.stat().st_mode & 0o777 == 0o600


def test_late_observations_bound_calendar_range_without_inventing_exact_total(db_path):
    for day, count in ((1, 12), (2, 15), (3, 19), (4, 25)):
        _capture(db_path, day, count, minute=1)
    result = report(db_path, _INSTALLER, _at(2), _at(4))
    assert result["coverage"] == "complete"
    assert result["exact_counter_delta"] is None
    assert result["lower_bound"] == 4
    assert result["upper_bound"] == 13
    assert result["observations"][0]["delay_seconds"] == 60
    actual = report(db_path, _INSTALLER, _at(2, 1), _at(4, 1))
    assert actual["exact_counter_delta"] == 10


def test_counter_reset_and_missed_slot_have_no_bridged_delta(db_path):
    for day, count in ((1, 7), (2, 3), (3, 4), (5, 10), (6, 12)):
        _capture(db_path, day, count)
    result = report(db_path, _INSTALLER, _at(1), _at(6))
    assert [gap["reason"] for gap in result["gaps"]] == ["counter_reset", "missed_slot"]
    assert [interval["counter_delta"] for interval in result["intervals"]] == [1, 2]
    assert result["coverage"] == "incomplete"
    assert result["exact_counter_delta"] is result["upper_bound"] is None
    assert result["lower_bound"] == 3
    reset_range = report(db_path, _INSTALLER, _at(2), _at(3))
    assert reset_range["exact_counter_delta"] == 1


def test_replacement_asset_is_neither_auto_approved_nor_subtracted(db_path):
    replacement = ApprovedInstaller(14, 93, _INSTALLER.version, _INSTALLER.size, _DIGEST)
    _capture(db_path, 1, 100)
    first = capture(
        db_path, _INSTALLER, _at(2).date(),
        fetch=lambda _: _metadata(2, replacement), clock=lambda: _at(2),
    )
    assert first.status == "asset_unavailable"
    _capture(db_path, 2, 2, installer=replacement)
    _capture(db_path, 3, 7, installer=replacement)
    removed = report(db_path, _INSTALLER, _at(1), _at(3))
    approved = report(db_path, replacement, _at(2), _at(3))
    assert removed["lower_bound"] is removed["exact_counter_delta"] is None
    assert approved["exact_counter_delta"] == 5


def test_unpinned_digest_changes_create_discontinuity(db_path):
    installer = ApprovedInstaller(14, 91, _INSTALLER.version, _INSTALLER.size)
    _capture(db_path, 1, 10, installer=installer)
    changed = "sha256:" + "2" * 64
    _capture(db_path, 2, 11, installer=installer, digest=changed)
    _capture(db_path, 3, 16, installer=installer, digest=changed)
    whole = report(db_path, installer, _at(1), _at(3))
    assert whole["gaps"][0]["reason"] == "digest_changed"
    assert whole["lower_bound"] == 5
    assert whole["upper_bound"] is None


@pytest.mark.parametrize(("status", "expected"), [(404, "asset_unavailable"),
                                                  (429, "provider_unavailable")])
def test_provider_errors_are_immutable_gaps(db_path, status, expected):
    _capture(db_path, 1, 5)

    def unavailable(_: int) -> object:
        raise HTTPError("https://api.github.com", status, _CANARY, {}, None)

    gap = capture(db_path, _INSTALLER, _at(2).date(), fetch=unavailable, clock=lambda: _at(2))
    assert gap.status == expected
    assert gap.count is None
    # A retry retains the original observation, even when the provider recovers.
    assert _capture(db_path, 2, 9) == gap
    _capture(db_path, 3, 10)
    result = report(db_path, _INSTALLER, _at(1), _at(3))
    assert result["coverage"] == "incomplete"
    assert result["exact_counter_delta"] is None
    assert _CANARY not in json.dumps(result)


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", "arbitrary.exe"), ("state", "open"), ("size", 0),
     ("digest", "sha256:" + "2" * 64), ("digest", None), ("download_count", True),
     ("download_count", -1), ("download_count", 2**63),
     ("browser_download_url", "https://other.invalid/not-allowed")],
)
def test_unapproved_provider_metadata_never_counts(db_path, field, value):
    data = _metadata(15)
    data["assets"][0][field] = value
    sample = capture(
        db_path, _INSTALLER, _at(1).date(),
        fetch=lambda _: data, clock=lambda: _at(1),
    )
    assert sample.status == "identity_mismatch"
    assert sample.count is None


def test_calendar_edges_without_observations_are_unavailable(db_path):
    empty = report(db_path, _INSTALLER, _at(1), _at(2))
    assert empty["coverage"] == "incomplete"
    assert empty["lower_bound"] is empty["upper_bound"] is None
    _capture(db_path, 2, 0)
    baseline = report(db_path, _INSTALLER, _at(1), _at(3))
    assert baseline["latest_provider_observation"]["provider_count"] == 0
    assert baseline["exact_counter_delta"] is None
    with pytest.raises(ValueError, match="INVALID_DATE_RANGE"):
        report(db_path, _INSTALLER, _at(2), _at(1))
    with pytest.raises(ValueError, match="UTC_REQUIRED"):
        report(db_path, _INSTALLER, datetime(2030, 4, 1), _at(2))


def test_late_cross_slot_observations_never_double_count(db_path):
    _capture(db_path, 1, 4)
    _capture(db_path, 2, 6)
    capture(
        db_path, _INSTALLER, _at(3).date(),
        fetch=lambda _: _metadata(12), clock=lambda: _at(5, 1),
    )
    _capture(db_path, 4, 9)
    _capture(db_path, 5, 11)
    _capture(db_path, 6, 20)
    result = report(db_path, _INSTALLER, _at(1), _at(6))
    assert "observation_order" in [gap["reason"] for gap in result["gaps"]]
    assert result["exact_counter_delta"] is None
    intervals = result["intervals"]
    assert all(
        before["end_utc"] <= after["start_utc"] for before, after in zip(intervals, intervals[1:])
    )
    assert result["lower_bound"] == 4


def test_concurrent_writers_commit_one_immutable_observation(db_path):
    barrier = Barrier(2)

    def writer(count):
        def fetch(_: int):
            barrier.wait(timeout=5)
            return _metadata(count)

        return capture(db_path, _INSTALLER, _at(1).date(), fetch=fetch, clock=lambda: _at(1))

    with ThreadPoolExecutor(max_workers=2) as workers:
        first, second = workers.map(writer, (100, 200))
    assert first == second
    assert first.count in (100, 200)
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM installer_snapshot_v1").fetchone() == (1,)


def test_owner_only_database_and_separate_schema_checked_before_provider(db_path, tmp_path):
    def unexpected(_: int):
        pytest.fail("Invalid stores must be rejected before provider contact")

    alias = db_path.with_name("symlink.sqlite")
    alias.symlink_to(db_path)
    with pytest.raises(ValueError, match="UNSAFE_LINK"):
        capture(alias, _INSTALLER, _at(1).date(), fetch=unexpected, clock=lambda: _at(1))
    db_path.chmod(0o644)
    with pytest.raises(ValueError, match="UNSAFE_FILE"):
        report(db_path, _INSTALLER, _at(1), _at(2))
    db_path.chmod(0o600)
    db_path.parent.chmod(0o755)
    with pytest.raises(ValueError, match="UNSAFE_DIRECTORY"):
        initialize(db_path.with_name("new.sqlite"))
    db_path.parent.chmod(0o700)
    other = db_path.with_name("other.sqlite")
    other.touch(mode=0o600)
    with pytest.raises(ValueError, match="UNSUPPORTED_SNAPSHOT_SCHEMA"):
        capture(other, _INSTALLER, _at(1).date(), fetch=unexpected, clock=lambda: _at(1))
    with pytest.raises(OSError):
        initialize(db_path)
    assert not (tmp_path / "new.sqlite").exists()


def test_public_metadata_request_has_fixed_endpoint_and_no_credentials(monkeypatch):
    class FakeOpener:
        def open(self, request: Request, *, timeout: int):
            assert request.full_url == (
                "https://api.github.com/repos/SoroushVahidi/njit-thesis-auditor-desktop/releases/14"
            )
            assert request.get_method() == "GET"
            assert timeout == 8
            assert all(key.lower() != "authorization" for key in request.headers)
            assert request.headers["Accept"] == "application/vnd.github+json"
            return io.BytesIO(json.dumps(_metadata(4)).encode())

    def opener(redirect, proxy):
        assert redirect.redirect_request(None, None, 302, "", {}, "https://bad.invalid/") is None
        assert isinstance(proxy, ProxyHandler)
        assert proxy.proxies == {}
        return FakeOpener()

    monkeypatch.setenv("GH_TOKEN", _CANARY)
    monkeypatch.setattr(downloads, "build_opener", opener)
    assert downloads._fetch_release(14) == _metadata(4)


def test_future_slots_fail_before_network_access(db_path):
    def unexpected(_: int) -> object:
        pytest.fail("A future slot must never fetch provider metadata")

    with pytest.raises(ValueError, match="FUTURE_SLOT"):
        capture(db_path, _INSTALLER, date(2030, 5, 1), fetch=unexpected, clock=lambda: _at(1))
    assert report(db_path, _INSTALLER, _at(1), _at(2))["observations"] == []


def test_operator_cli_initializes_reads_and_captures_synthetic_metadata(tmp_path, capsys):
    import runpy

    script = Path(__file__).resolve().parents[1] / "scripts" / "snapshot_installer_downloads.py"
    main = runpy.run_path(str(script))["main"]
    main.__globals__["APPROVED_INSTALLERS"] = (_INSTALLER,)

    def synthetic_capture(path: Path, installer: ApprovedInstaller, slot: date):
        assert installer == _INSTALLER
        return _capture(path, slot.day, slot.day * 3)

    main.__globals__["capture"] = synthetic_capture
    tmp_path.chmod(0o700)
    path = tmp_path / "operator.sqlite"
    args = ["--db", str(path)]
    assert main([*args, "init"]) == 0
    assert main([*args, "capture", "--slot", "2030-04-01"]) == 0
    assert main([*args, "capture", "--slot", "2030-04-02"]) == 0
    summaries = capsys.readouterr().out
    assert '"asset_id": 91' in summaries
    assert _CANARY not in summaries
    assert main([*args, "report", "--start", "2030-04-01", "--end", "2030-04-02"]) == 0
    result, = json.loads(capsys.readouterr().out)
    assert result["exact_counter_delta"] == 3
    assert result["activity_classification"] == "unclassified"

    path.chmod(0o644)
    assert main([*args, "report", "--start", "2030-04-01", "--end", "2030-04-02"]) == 1
    failure = capsys.readouterr()
    assert not failure.out
    assert str(path) not in failure.err
