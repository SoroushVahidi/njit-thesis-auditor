"""Privacy-safe case fingerprinting and equivalence.

A fingerprint answers one question: is a finding produced by a later
auditor run the *same* case, an *equivalent* case, or a *materially new*
case, compared to one already in the ledger?

Inputs are always structural/numeric -- a thesis-version id, an internal
rule id, an issue type, a physical page, a caller-built structural
location string, and an optional "volatile detail" string -- never raw
dissertation text. Callers are responsible for keeping those inputs
privacy-safe (e.g. ``"list_of_tables:entry_index=3"``, not the entry's
title text).

Two digests are produced from the same inputs, split along a stability
boundary:

- ``equivalence_key`` -- hashes only the *stable* structural identity:
  thesis version, rule, issue type, physical page, and
  ``structural_location``. Two findings with the same equivalence key are
  "the same violation, structurally speaking" -- this is what
  ``make_case_id`` is built from, so a case keeps its identity across
  reruns even if fine details shift.
- ``exact_fingerprint`` -- the equivalence key's inputs plus
  ``volatile_detail`` (e.g. a rounded measurement, a short geometry
  bucket). Two findings only share this when nothing -- not even the
  volatile detail -- changed.

Classification for a new finding against the ledger:

- **SAME CASE**: new finding's ``exact_fingerprint`` matches an existing
  case's.
- **EQUIVALENT CASE**: exact fingerprints differ, but ``equivalence_key``
  matches -- same underlying violation, minor detail drift (e.g. a few
  points of bbox movement from a wrapping change, or a rounded
  measurement crossing a bucket boundary). Reuse the existing case id;
  do not re-present it as new if it was already adjudicated.
- **NEW CASE**: ``equivalence_key`` does not match anything on that page
  for that thesis version/rule/issue type -- a materially different
  violation (or the first time this one has been seen).

``structural_location`` must be granular enough that two distinct
violations on the same page do not collide (e.g. include an entry index
or figure/table number, not just the page), or they will incorrectly be
treated as the same case.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

_FINGERPRINT_HASH_LENGTH = 32


def _digest(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:_FINGERPRINT_HASH_LENGTH]


@dataclass(frozen=True)
class CaseFingerprint:
    exact_fingerprint: str
    equivalence_key: str


def compute_case_fingerprint(
    *,
    thesis_version_id: str,
    internal_rule_id: str,
    issue_type: str,
    physical_page: int | None,
    structural_location: str,
    volatile_detail: str = "",
) -> CaseFingerprint:
    """Compute a case's exact fingerprint and (coarser) equivalence key.

    Raises ``ValueError`` if any stable-identity input is empty, since an
    empty component would silently widen what counts as "the same case".
    """
    if not thesis_version_id:
        raise ValueError("thesis_version_id must not be empty")
    if not internal_rule_id:
        raise ValueError("internal_rule_id must not be empty")
    if not issue_type:
        raise ValueError("issue_type must not be empty")
    if not structural_location:
        raise ValueError("structural_location must not be empty")

    stable_parts = (
        thesis_version_id,
        internal_rule_id,
        issue_type,
        "" if physical_page is None else str(physical_page),
        structural_location,
    )
    equivalence_key = _digest(*stable_parts)
    exact_fingerprint = _digest(*stable_parts, volatile_detail)
    return CaseFingerprint(exact_fingerprint=exact_fingerprint, equivalence_key=equivalence_key)


def classify_against_known(
    new_fingerprint: CaseFingerprint,
    known_fingerprints: list[CaseFingerprint],
) -> str:
    """Classify ``new_fingerprint`` against a list of already-known ones.

    Returns one of ``"SAME"``, ``"EQUIVALENT"``, or ``"NEW"``. Checks exact
    matches first so an identical rerun is never merely "equivalent" to
    itself.
    """
    for known in known_fingerprints:
        if new_fingerprint.exact_fingerprint == known.exact_fingerprint:
            return "SAME"
    for known in known_fingerprints:
        if new_fingerprint.equivalence_key == known.equivalence_key:
            return "EQUIVALENT"
    return "NEW"
