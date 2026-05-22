"""Core models used by the auditor."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for audit findings."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class AuditFinding(BaseModel):
    """A single finding returned by a rule."""

    rule_id: str
    severity: Severity
    message: str
    page: int | None = None
    details: dict[str, str] = Field(default_factory=dict)


class PageInfo(BaseModel):
    """Geometry and indexing details for a page."""

    page_index: int
    width: float
    height: float


class DocumentInfo(BaseModel):
    """Top-level PDF metadata used by rules."""

    path: str
    page_count: int
    pages: list[PageInfo]
