"""Closed, immutable scalar observations; no request or document data."""

from __future__ import annotations

import json
import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import ClassVar, Literal

METRICS = ("page_view", "upload_accepted", "audit_completed", "audit_failed")
OUTCOMES = ("completed", "failed")
Outcome = Literal["completed", "failed"]


def validate_day(value: str) -> None:
    if type(value) is not str or len(value) != 10 or date.fromisoformat(value).isoformat() != value:
        raise ValueError("INVALID_DAY")


def utc_now(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise ValueError("INVALID_CLOCK")
    return value


def duration_bucket(seconds: float) -> int:
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError("INVALID_DURATION")
    return bisect_right((1, 5, 15, 30, 60, 120, 300), seconds)


@dataclass(frozen=True, slots=True)
class PageView:
    day_utc: str
    kind: ClassVar[str] = "page_view"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        validate_day(self.day_utc)


@dataclass(frozen=True, slots=True)
class UploadAccepted:
    day_utc: str
    kind: ClassVar[str] = "upload_accepted"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        validate_day(self.day_utc)


@dataclass(frozen=True, slots=True)
class AuditTerminal:
    day_utc: str
    outcome: Outcome
    duration_bucket: int | None
    kind: ClassVar[str] = "audit_terminal"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        validate_day(self.day_utc)
        if type(self.outcome) is not str or self.outcome not in OUTCOMES:
            raise ValueError("INVALID_OUTCOME")
        if self.duration_bucket is not None and (
            type(self.duration_bucket) is not int or not 0 <= self.duration_bucket <= 7
        ):
            raise ValueError("INVALID_BUCKET")


Event = PageView | UploadAccepted | AuditTerminal


def encode(event: Event) -> bytes:
    if type(event) not in (PageView, UploadAccepted, AuditTerminal):
        raise ValueError("INVALID_EVENT")
    event.__post_init__()
    payload: dict[str, str | int | None] = {
        "schema_version": 1,
        "kind": event.kind,
        "day_utc": event.day_utc,
    }
    if isinstance(event, AuditTerminal):
        payload.update(outcome=event.outcome, duration_bucket=event.duration_bucket)
    result = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if len(result) > 256:
        raise ValueError("OVERSIZE_EVENT")
    return result


def decode(payload: bytes) -> Event:
    if type(payload) is not bytes or len(payload) > 256:
        raise ValueError("INVALID_ENVELOPE")
    obj = json.loads(payload)
    if type(obj) is not dict or type(obj.get("schema_version")) is not int:
        raise ValueError("INVALID_EVENT")
    if obj.pop("schema_version") != 1:
        raise ValueError("INVALID_VERSION")
    kind = obj.pop("kind", None)
    classes = {
        "page_view": PageView,
        "upload_accepted": UploadAccepted,
        "audit_terminal": AuditTerminal,
    }
    if kind not in classes:
        raise ValueError("INVALID_KIND")
    return classes[kind](**obj)
