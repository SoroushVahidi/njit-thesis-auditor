"""Stable ID grammar for the Ester review ledger.

Two families of ID exist here, and callers should know which they are
getting:

**Content-addressed / deterministic** -- ``make_thesis_id``,
``make_thesis_version_id``, ``make_case_id``. Calling these again with the
same inputs always yields the same ID. This is what lets a case reviewed
in one round be recognized as "the same case" (or "an equivalent case") in
a later round without a lookup table.

**Event / occurrence** -- ``make_run_id``, ``make_adjudication_id``,
``make_history_event_id``. Two calls are never equal, even with identical
inputs, because each represents a distinct real-world occurrence (running
the auditor twice against the same code+input is still two runs; two
reviewers can independently adjudicate the same case). These embed a
timestamp for rough chronological sorting plus a random suffix for
uniqueness -- they are not meant to be reconstructed, only recorded.

``make_review_round_id`` is a third, hybrid shape: human-assigned rather
than content-addressed, but constrained to a sortable ``ER-YYYYMMDD-NN``
grammar (date plus a small caller-supplied sequence number, so a caller
must ask the store for the next free sequence rather than this module
guessing at global state).

None of the deterministic IDs are computed from dissertation body text --
only from a caller-supplied stable alias (for ``Thesis``) or a content
hash (for ``ThesisVersion``) or other already-opaque ids/structural
strings (for ``ReviewCase``, via its fingerprint's equivalence key).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets

_ID_HASH_LENGTH = 12


def _short_hash(*parts: str, length: int = _ID_HASH_LENGTH) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:length]


def make_thesis_id(external_key: str) -> str:
    """Deterministic thesis identity from a caller-supplied stable alias.

    ``external_key`` must be a stable, evaluator-assigned alias (e.g. an
    existing corpus short name such as ``"praneeth"``) -- never full body
    text, never a filesystem path. The alias itself is hashed away, not
    stored as the id, so the id alone reveals nothing about the alias.
    """
    external_key = external_key.strip()
    if not external_key:
        raise ValueError("external_key must not be empty")
    return f"TH-{_short_hash(external_key)}"


def make_thesis_version_id(thesis_id: str, sha256_hex: str) -> str:
    """Deterministic version identity: thesis identity + artifact content hash.

    Two different PDFs for the same thesis (different ``sha256_hex``)
    always get different version ids; re-deriving the id for the same
    thesis + the same bytes always reproduces the same id.
    """
    if not sha256_hex:
        raise ValueError("sha256_hex must not be empty")
    return f"TV-{_short_hash(thesis_id, sha256_hex)}"


def make_run_id(code_sha: str) -> str:
    """Unique id for one auditor execution. Not deterministic -- see module docstring."""
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"RUN-{code_sha[:8]}-{timestamp}-{secrets.token_hex(4)}"


def make_review_round_id(review_date: dt.date, sequence: int) -> str:
    """Sortable, human-readable review-round id: ``ER-YYYYMMDD-NN``.

    ``sequence`` (1-99) must be supplied by the caller -- typically "one
    past the highest existing sequence for this date in the store" -- this
    module does not consult any global state.
    """
    if not (1 <= sequence <= 99):
        raise ValueError("sequence must be between 1 and 99")
    return f"ER-{review_date:%Y%m%d}-{sequence:02d}"


def make_case_id(thesis_version_id: str, internal_rule_id: str, equivalence_key: str) -> str:
    """Deterministic case identity from structural identity, not physical page alone.

    Built from the case's fingerprint *equivalence key* (see
    ``njit_auditor.review_ledger.fingerprint``), not its exact fingerprint,
    so a case that recurs with only a minor wording/geometry change keeps
    the same case id -- the property "stable enough to reference
    permanently after Ester reviews it" requires this.
    """
    if not equivalence_key:
        raise ValueError("equivalence_key must not be empty")
    return f"CASE-{_short_hash(thesis_version_id, internal_rule_id, equivalence_key)}"


def make_adjudication_id() -> str:
    """Unique id for one human judgment event. Not deterministic."""
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"ADJ-{timestamp}-{secrets.token_hex(4)}"


def make_resolution_id() -> str:
    """Unique id for one resolution record. Not deterministic."""
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"RES-{timestamp}-{secrets.token_hex(4)}"


def make_regression_result_id() -> str:
    """Unique id for one regression-replay result. Not deterministic."""
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"REG-{timestamp}-{secrets.token_hex(4)}"


def make_history_event_id() -> str:
    """Unique id for one append-only history event. Not deterministic."""
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    return f"EVT-{timestamp}-{secrets.token_hex(4)}"
