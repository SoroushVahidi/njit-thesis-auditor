"""Closed, immutable scalar observations; no request or document data."""

from __future__ import annotations

import json
import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import ClassVar, Literal

SOURCES = ("unknown", "upload", "approved_sample")
Source = Literal["unknown", "upload", "approved_sample"]
SUBMISSION_METRICS = ("submission_attempted", "upload_accepted")
OUTCOMES = ("completed", "failed")
Outcome = Literal["completed", "failed"]
AUDIT_METRICS = ("audit_completed", "audit_failed")
REPORT_FORMATS = (
    "complete_pdf", "focused_pdf", "comments_pdf", "json", "markdown", "text", "legacy_pdf"
)
ReportFormat = Literal[
    "complete_pdf", "focused_pdf", "comments_pdf", "json", "markdown", "text", "legacy_pdf"
]
REPORT_RESPONSES = ("full", "partial")
ResponseKind = Literal["full", "partial"]
SOURCE_METRICS = (*SUBMISSION_METRICS, *AUDIT_METRICS)
PUBLIC_METRICS = (
    "page_view",
    *SOURCE_METRICS,
    *(f"{metric}_{source}" for metric in SOURCE_METRICS for source in SOURCES[1:]),
    *(f"report_{fmt}_{response}" for fmt in REPORT_FORMATS for response in REPORT_RESPONSES),
)
METRICS = (*PUBLIC_METRICS, *(f"internal_{metric}" for metric in PUBLIC_METRICS))


def validate_day(value: str) -> None:
    if type(value) is not str or len(value) != 10 or date.fromisoformat(value).isoformat() != value:
        raise ValueError("INVALID_DAY")


def _validate_internal(internal: bool) -> None:
    if type(internal) is not bool:
        raise ValueError("INVALID_ACTIVITY")


def _validate_source(source: Source) -> None:
    if type(source) is not str or source not in SOURCES:
        raise ValueError("INVALID_SOURCE")


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
    internal: bool = False
    kind: ClassVar[str] = "page_view"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        validate_day(self.day_utc)
        _validate_internal(self.internal)


@dataclass(frozen=True, slots=True)
class SubmissionAttempted:
    day_utc: str
    source: Source
    internal: bool = False
    kind: ClassVar[str] = "submission_attempted"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        validate_day(self.day_utc)
        _validate_source(self.source)
        _validate_internal(self.internal)


@dataclass(frozen=True, slots=True)
class UploadAccepted:
    day_utc: str
    source: Source = "unknown"
    internal: bool = False
    kind: ClassVar[str] = "upload_accepted"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        validate_day(self.day_utc)
        _validate_source(self.source)
        _validate_internal(self.internal)


@dataclass(frozen=True, slots=True)
class AuditTerminal:
    day_utc: str
    outcome: Outcome
    duration_bucket: int | None
    source: Source = "unknown"
    internal: bool = False
    kind: ClassVar[str] = "audit_terminal"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        validate_day(self.day_utc)
        _validate_source(self.source)
        _validate_internal(self.internal)
        if type(self.outcome) is not str or self.outcome not in OUTCOMES:
            raise ValueError("INVALID_OUTCOME")
        if self.duration_bucket is not None and (
            type(self.duration_bucket) is not int or not 0 <= self.duration_bucket <= 7
        ):
            raise ValueError("INVALID_BUCKET")


@dataclass(frozen=True, slots=True)
class ReportResponse:
    day_utc: str
    format: ReportFormat
    response: ResponseKind
    internal: bool = False
    kind: ClassVar[str] = "report_response"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        validate_day(self.day_utc)
        _validate_internal(self.internal)
        if type(self.format) is not str or self.format not in REPORT_FORMATS:
            raise ValueError("INVALID_REPORT_FORMAT")
        if type(self.response) is not str or self.response not in REPORT_RESPONSES:
            raise ValueError("INVALID_RESPONSE_KIND")


Event = PageView | SubmissionAttempted | UploadAccepted | AuditTerminal | ReportResponse


def event_metrics(event: Event) -> tuple[str, ...]:
    metrics: tuple[str, ...]
    if isinstance(event, ReportResponse):
        metrics = (f"report_{event.format}_{event.response}",)
    else:
        metric = f"audit_{event.outcome}" if isinstance(event, AuditTerminal) else event.kind
        metrics = (metric,)
        if not isinstance(event, PageView) and event.source != "unknown":
            metrics += (f"{metric}_{event.source}",)
    if event.internal:
        metrics += tuple(f"internal_{metric}" for metric in metrics)
    return metrics


def encode(event: Event) -> bytes:
    if type(event) not in (
        PageView, SubmissionAttempted, UploadAccepted, AuditTerminal, ReportResponse
    ):
        raise ValueError("INVALID_EVENT")
    event.__post_init__()
    payload: dict[str, str | int | None] = {
        "schema_version": 1,
        "kind": event.kind,
        "day_utc": event.day_utc,
        "internal": event.internal,
    }
    if isinstance(event, (SubmissionAttempted, UploadAccepted, AuditTerminal)):
        payload["source"] = event.source
    if isinstance(event, AuditTerminal):
        payload.update(outcome=event.outcome, duration_bucket=event.duration_bucket)
    if isinstance(event, ReportResponse):
        payload.update(format=event.format, response=event.response)
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
        "submission_attempted": SubmissionAttempted,
        "upload_accepted": UploadAccepted,
        "audit_terminal": AuditTerminal,
        "report_response": ReportResponse,
    }
    if kind not in classes:
        raise ValueError("INVALID_KIND")
    return classes[kind](**obj)
