"""Private observations of approved public installer counters."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .store import validate_path

_REPOSITORY = "SoroushVahidi/njit-thesis-auditor-desktop"
_MAX_RESPONSE = 1_048_576
_DAY = timedelta(days=1)
_DDL = """
CREATE TABLE installer_snapshot_v1 (
    release_id INTEGER NOT NULL CHECK(release_id > 0),
    asset_id INTEGER NOT NULL CHECK(asset_id > 0),
    version TEXT NOT NULL,
    slot_utc TEXT NOT NULL,
    observed_at_utc TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN
       ('observed','provider_unavailable','asset_unavailable','identity_mismatch')),
    digest TEXT,
    download_count INTEGER,
    CHECK((status = 'observed' AND typeof(download_count) = 'integer' AND download_count >= 0)
       OR (status <> 'observed' AND digest IS NULL AND download_count IS NULL)),
    PRIMARY KEY(release_id, asset_id, slot_utc)
) WITHOUT ROWID;
"""


@dataclass(frozen=True)
class ApprovedInstaller:
    """The fixed provider identity approved for observation."""

    release_id: int
    asset_id: int
    version: str
    size: int
    digest: str | None = None
    active: bool = True

    @property
    def tag(self) -> str:
        return f"desktop-v{self.version}"

    @property
    def filename(self) -> str:
        return f"NJIT-Thesis-Auditor-Setup-{self.version}.exe"


APPROVED_INSTALLERS = (
    ApprovedInstaller(
        433426367,
        707862489,
        "0.2.0-rc.3",
        41326578,
        "sha256:70713e44f18aaac32d5cc244aee3c82c7badbd8ce9d9dbf3b1dffe919a05f690",
    ),
)


@dataclass(frozen=True)
class Snapshot:
    slot: date
    observed_at: datetime
    status: str
    digest: str | None = None
    count: int | None = None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fetch_release(release_id: int) -> object:
    request = Request(
        f"https://api.github.com/repos/{_REPOSITORY}/releases/{release_id}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "NJIT-Installer-Counter-Snapshots",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    opener = build_opener(_NoRedirect(), ProxyHandler({}))
    with opener.open(request, timeout=8) as response:
        payload = response.read(_MAX_RESPONSE + 1)
    if len(payload) > _MAX_RESPONSE:
        raise ValueError("OVERSIZE_PROVIDER_RESPONSE")
    return json.loads(payload)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("UTC_REQUIRED")
    return value.astimezone(timezone.utc)


def _provider_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("INVALID_PROVIDER_TIMESTAMP")
    return _utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _validate_installer(release: object, installer: ApprovedInstaller) -> tuple[str | None, int]:
    if (
        not isinstance(release, dict)
        or release.get("id") != installer.release_id
        or release.get("tag_name") != installer.tag
        or release.get("draft") is not False
        or release.get("prerelease") is not True
    ):
        raise ValueError("INVALID_RELEASE_IDENTITY")
    _provider_time(release.get("published_at"))
    assets = release.get("assets")
    if not isinstance(assets, list) or len(assets) >= 100:
        raise ValueError("INCOMPLETE_ASSETS")
    matches = [
        asset for asset in assets
        if isinstance(asset, dict) and asset.get("id") == installer.asset_id
    ]
    if not matches:
        raise LookupError("ASSET_UNAVAILABLE")
    if len(matches) != 1:
        raise ValueError("DUPLICATE_ASSET")
    asset = matches[0]
    expected_url = (
        f"https://github.com/{_REPOSITORY}/releases/download/{installer.tag}/{installer.filename}"
    )
    count = asset.get("download_count")
    digest = asset.get("digest")
    if (
        asset.get("name") != installer.filename
        or asset.get("size") != installer.size
        or asset.get("state") != "uploaded"
        or asset.get("browser_download_url") != expected_url
        or (installer.digest is not None and digest != installer.digest)
        or (digest is not None and (not isinstance(digest, str)
                                   or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)))
        or type(count) is not int
        or not 0 <= count < 2**63
    ):
        raise ValueError("INVALID_ASSET_IDENTITY")
    _provider_time(asset.get("created_at"))
    return digest, count


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    validate_path(path)
    db = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True)
    try:
        if db.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
            raise ValueError("UNSUPPORTED_JOURNAL")
        if readonly:
            db.execute("PRAGMA query_only=ON")
        else:
            db.execute("PRAGMA synchronous=FULL")
        return db
    except Exception:
        db.close()
        raise


def _verify_schema(db: sqlite3.Connection) -> None:
    existing = db.execute("SELECT sql FROM sqlite_schema ORDER BY type,name").fetchall()
    if existing != [(_DDL.strip().removesuffix(";"),)]:
        raise ValueError("UNSUPPORTED_SNAPSHOT_SCHEMA")


def initialize(path: Path) -> None:
    """Provision a new snapshot database in an existing owner-only directory."""
    validate_path(path, existing=False)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    with closing(_connect(path)) as db, db:
        db.execute(_DDL)


def capture(
    path: Path,
    installer: ApprovedInstaller,
    slot: date,
    *,
    fetch: Callable[[int], object] = _fetch_release,
    clock: Callable[[], datetime] = _now,
) -> Snapshot:
    """Record one immutable observation for an intended UTC midnight slot."""
    if slot > _utc(clock()).date():
        raise ValueError("FUTURE_SLOT")
    with closing(_connect(path, readonly=True)) as db:
        _verify_schema(db)
        existing = db.execute(
            """SELECT slot_utc, observed_at_utc, status, digest, download_count
               FROM installer_snapshot_v1 WHERE release_id=? AND asset_id=? AND slot_utc=?""",
            (installer.release_id, installer.asset_id, slot.isoformat()),
        ).fetchone()
        if existing is not None:
            return _snapshot(existing)

    digest = count = None
    status = "observed"
    try:
        release = fetch(installer.release_id)
    except HTTPError as exc:
        status = "asset_unavailable" if exc.code == 404 else "provider_unavailable"
        exc.close()
    except (OSError, ValueError):
        status = "provider_unavailable"
    else:
        try:
            digest, count = _validate_installer(release, installer)
        except LookupError:
            status = "asset_unavailable"
        except ValueError:
            status = "identity_mismatch"
    actual = _utc(clock())
    if actual.date() < slot:
        raise ValueError("CLOCK_BEFORE_SLOT")

    with closing(_connect(path)) as db, db:
        _verify_schema(db)
        db.execute(
            """INSERT INTO installer_snapshot_v1 VALUES(?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(release_id, asset_id, slot_utc) DO NOTHING""",
            (installer.release_id, installer.asset_id, installer.version, slot.isoformat(),
             actual.isoformat(), status, digest, count),
        )
        stored = db.execute(
            """SELECT slot_utc, observed_at_utc, status, digest, download_count
               FROM installer_snapshot_v1 WHERE release_id=? AND asset_id=? AND slot_utc=?""",
            (installer.release_id, installer.asset_id, slot.isoformat()),
        ).fetchone()
    return _snapshot(stored)


def _snapshot(row: tuple[Any, ...]) -> Snapshot:
    slot, observed_at, status, digest, count = row
    return Snapshot(date.fromisoformat(slot), _utc(datetime.fromisoformat(observed_at)),
                    status, digest, count)


def snapshot_details(snapshot: Snapshot) -> dict[str, Any]:
    """Return the safe public-counter fields recorded for one observation."""
    midnight = datetime.combine(snapshot.slot, datetime.min.time(), timezone.utc)
    return {
        "slot_utc": snapshot.slot.isoformat(),
        "observed_at_utc": snapshot.observed_at.isoformat(),
        "delay_seconds": (snapshot.observed_at - midnight).total_seconds(),
        "status": snapshot.status,
        "provider_count": snapshot.count,
        "asset_digest": snapshot.digest,
    }


def _gap(before: Snapshot, after: Snapshot) -> str | None:
    if after.observed_at <= before.observed_at or after.slot <= before.slot:
        return "observation_order"
    if after.slot - before.slot != _DAY:
        return "missed_slot"
    if before.count is None or after.count is None:
        return "unavailable_observation"
    if before.digest != after.digest:
        return "digest_changed"
    if after.count < before.count:
        return "counter_reset"
    return None


def report(
    path: Path, installer: ApprovedInstaller, start: datetime, end: datetime
) -> dict[str, Any]:
    """Report one asset's observed counter intervals and conservative range bounds."""
    start, end = _utc(start), _utc(end)
    if start >= end:
        raise ValueError("INVALID_DATE_RANGE")
    with closing(_connect(path, readonly=True)) as db:
        _verify_schema(db)
        rows = db.execute(
            """SELECT slot_utc, observed_at_utc, status, digest, download_count
               FROM installer_snapshot_v1 WHERE release_id=? AND asset_id=?
               ORDER BY slot_utc""",
            (installer.release_id, installer.asset_id),
        )
        points = [_snapshot(row) for row in rows]

    intervals = []
    gaps = []
    lower = upper = 0
    covered_until = start
    exact_start = exact_end = False
    chronological = sorted(points, key=lambda point: point.observed_at)
    for before, after in zip(chronological, chronological[1:]):
        left, right = before.observed_at, after.observed_at
        if max(left, right) <= start or min(left, right) >= end:
            continue
        reason = _gap(before, after)
        if reason:
            gaps.append({
                "start_slot_utc": before.slot.isoformat(),
                "end_slot_utc": after.slot.isoformat(),
                "reason": reason,
            })
            continue
        assert before.count is not None and after.count is not None
        delta = after.count - before.count
        intervals.append({
            "start_utc": left.isoformat(),
            "end_utc": right.isoformat(),
            "counter_delta": delta,
        })
        upper += delta
        if left >= start and right <= end:
            lower += delta
        if left <= covered_until < right:
            covered_until = right
        exact_start |= left == start
        exact_end |= right == end
    complete = covered_until >= end and not gaps
    latest = max((item for item in points if item.count is not None),
                 key=lambda item: item.observed_at, default=None)
    return {
        "release_id": installer.release_id,
        "asset_id": installer.asset_id,
        "version": installer.version,
        "metric": "github_reported_download_counter",
        "activity_classification": "unclassified",
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "coverage": "complete" if complete else "incomplete",
        "exact_counter_delta": lower if complete and exact_start and exact_end else None,
        "lower_bound": lower if intervals else None,
        "upper_bound": upper if complete else None,
        "observations": [
            snapshot_details(point) for point in points if start <= point.observed_at <= end
        ],
        "intervals": intervals,
        "gaps": gaps,
        "latest_attempt": snapshot_details(chronological[-1]) if chronological else None,
        "latest_provider_observation": snapshot_details(latest) if latest else None,
    }
