"""Synthetic closed-schema, privacy and clock checks."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from njit_auditor.analytics.schema import (
    AuditTerminal,
    PageView,
    UploadAccepted,
    decode,
    duration_bucket,
    encode,
    utc_now,
)


class FakeClock:
    def __init__(self, now=None, mono=100.0):
        self.now = now or datetime(2030, 1, 1, tzinfo=timezone.utc)
        self.mono = mono

    def utcnow(self):
        return self.now

    def monotonic(self):
        return self.mono

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)
        self.mono += seconds


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0),
        (0.999, 0),
        (1, 1),
        (4.999, 1),
        (5, 2),
        (14.999, 2),
        (15, 3),
        (29.999, 3),
        (30, 4),
        (59.999, 4),
        (60, 5),
        (119.999, 5),
        (120, 6),
        (299.999, 6),
        (300, 7),
        (1000000, 7),
    ],
)
def test_buckets(value, expected):
    assert duration_bucket(value) == expected


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan"), "1", True, None])
def test_invalid_duration(value):
    with pytest.raises((ValueError, TypeError)):
        duration_bucket(value)


@pytest.mark.parametrize("day", ["20300101", "2030-1-01", "2030-02-29", "IP_CANARY", 1, None])
def test_bad_days(day):
    with pytest.raises((ValueError, TypeError)):
        PageView(day)


@pytest.mark.parametrize(
    "event",
    [
        PageView("2030-01-01"),
        UploadAccepted("2030-01-01"),
        AuditTerminal("2030-01-01", "completed", 7),
        AuditTerminal("2030-01-01", "failed", None),
    ],
)
def test_closed_immutable_bounded(event):
    assert decode(encode(event)) == event
    assert len(encode(event)) <= 256
    with pytest.raises(FrozenInstanceError):
        event.day_utc = "2031-01-01"
    with pytest.raises((TypeError, AttributeError)):
        event.filename = "PRIVATE_CANARY.pdf"


@pytest.mark.parametrize(
    "field",
    [
        "filename",
        "job_id",
        "ip",
        "ua",
        "url",
        "findings",
        "text",
        "cookie",
        "document_hash",
        "email",
        "elapsed_ms",
        "event_id",
    ],
)
def test_extra_fields_rejected(field):
    payload = b'{"schema_version":1,"kind":"page_view","day_utc":"2030-01-01",'
    payload += ('"' + field + '":"PRIVATE_CANARY"}').encode()
    with pytest.raises((ValueError, TypeError)):
        decode(payload)


@pytest.mark.parametrize(
    "payload",
    [
        b"{}",
        b"[]",
        b"x" * 257,
        b'{"schema_version":true,"kind":"page_view","day_utc":"2030-01-01"}',
        b'{"schema_version":2,"kind":"page_view","day_utc":"2030-01-01"}',
        b'{"schema_version":1,"kind":"other","day_utc":"2030-01-01"}',
    ],
)
def test_invalid_envelopes(payload):
    with pytest.raises((ValueError, TypeError)):
        decode(payload)


@pytest.mark.parametrize(
    "outcome,bucket",
    [("error", 1), ("failed", -1), ("failed", 8), ("failed", True), ("failed", 1.0)],
)
def test_invalid_terminal(outcome, bucket):
    with pytest.raises(ValueError):
        AuditTerminal("2030-01-01", outcome, bucket)


def test_utc_only():
    with pytest.raises(ValueError):
        utc_now(datetime(2030, 1, 1))
    with pytest.raises(ValueError):
        utc_now(datetime(2030, 1, 1, tzinfo=timezone(timedelta(hours=1))))
