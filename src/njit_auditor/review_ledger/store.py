"""Append-only JSONL storage for the Ester review ledger.

Format choice (see ``docs/evaluation/ESTER_REVIEW_DATA_MODEL.md`` for the
full rationale): one ``.jsonl`` file per entity type under a ledger root
directory, one canonical JSON object per line (sorted keys, so diffs are
line-level and reviewable in a PR). No server/database dependency --
``git diff`` on a ``.jsonl`` file is itself a serviceable audit trail
during this foundation phase, and the format is trivial to migrate from
(read) or into (write) an ``.xlsx`` workbook in a later phase.

``EsterReviewLedger`` loads a root directory into memory, validates
invariants (below), and is the only way records are supposed to be
appended -- direct file edits bypass validation and are not supported.

Invariants enforced here:

- **No duplicate ids** within any one collection.
- **No orphan references**: a ``ReviewCase`` must reference an existing
  ``ReviewRound``, ``AuditorRun``, and ``ThesisVersion`` (whose own
  ``thesis_id`` must exist); an ``Adjudication``/``Resolution``/
  ``RegressionResult`` must reference an existing ``ReviewCase``;
  ``ThesisVersion.thesis_id`` must exist; ``AuditorRun.thesis_version_id``
  must exist.
- **Linear, non-overwriting adjudication history**: adding a new
  ``Adjudication`` for a case that already has one requires
  ``supersedes_adjudication_id`` to name that case's *current* (not
  already-superseded) adjudication -- this is what prevents silently
  losing a prior human judgment. The earlier row is never edited or
  removed.
- **History is append-only** by construction: there is no update/delete
  method on this class for any collection, only ``add_*``/
  ``record_history_event``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from njit_auditor.review_ledger.models import (
    Adjudication,
    AuditorRun,
    HistoryEvent,
    RegressionResult,
    Resolution,
    ReviewCase,
    ReviewRound,
    Thesis,
    ThesisVersion,
)

SCHEMA_VERSION = 1

T = TypeVar("T")


class LedgerValidationError(ValueError):
    """Raised when an append would violate a ledger invariant."""


class _JsonlCollection:
    """One entity type's on-disk file plus its in-memory index."""

    def __init__(self, path: Path, id_field: str) -> None:
        self._path = path
        self._id_field = id_field
        self._by_id: dict[str, dict[str, object]] = {}
        self._order: list[str] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                record_id = str(record[self._id_field])
                if record_id in self._by_id:
                    raise LedgerValidationError(
                        f"{self._path.name}:{line_no}: duplicate id {record_id!r} on disk"
                    )
                self._by_id[record_id] = record
                self._order.append(record_id)

    def __contains__(self, record_id: str) -> bool:
        return record_id in self._by_id

    def get(self, record_id: str) -> dict[str, object] | None:
        return self._by_id.get(record_id)

    def all(self) -> list[dict[str, object]]:
        return [self._by_id[rid] for rid in self._order]

    def ids(self) -> list[str]:
        return list(self._order)

    def append(self, record_id: str, record: dict[str, object]) -> None:
        if record_id in self._by_id:
            raise LedgerValidationError(
                f"{self._path.name}: id {record_id!r} already exists (append-only: cannot "
                "overwrite -- create a superseding record instead)"
            )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        canonical_line = json.dumps(record, sort_keys=True, ensure_ascii=False)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(canonical_line + "\n")
        self._by_id[record_id] = record
        self._order.append(record_id)


class EsterReviewLedger:
    """In-memory-indexed, disk-backed handle onto one ledger root directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._meta_path = root / "_ledger_meta.json"
        self._write_or_check_meta()

        self.theses = _JsonlCollection(root / "theses.jsonl", "thesis_id")
        self.thesis_versions = _JsonlCollection(
            root / "thesis_versions.jsonl", "thesis_version_id"
        )
        self.auditor_runs = _JsonlCollection(root / "auditor_runs.jsonl", "run_id")
        self.review_rounds = _JsonlCollection(root / "review_rounds.jsonl", "review_round_id")
        self.review_cases = _JsonlCollection(root / "review_cases.jsonl", "case_id")
        self.adjudications = _JsonlCollection(root / "adjudications.jsonl", "adjudication_id")
        self.resolutions = _JsonlCollection(root / "resolutions.jsonl", "resolution_id")
        self.regression_results = _JsonlCollection(
            root / "regression_results.jsonl", "regression_result_id"
        )
        self.history_events = _JsonlCollection(root / "history_events.jsonl", "event_id")

    def _write_or_check_meta(self) -> None:
        if self._meta_path.exists():
            existing = json.loads(self._meta_path.read_text(encoding="utf-8"))
            found = existing.get("schema_version")
            if found != SCHEMA_VERSION:
                raise LedgerValidationError(
                    f"ledger at {self.root} has schema_version {found!r}, "
                    f"expected {SCHEMA_VERSION!r}"
                )
            return
        self._meta_path.parent.mkdir(parents=True, exist_ok=True)
        self._meta_path.write_text(
            json.dumps({"schema_version": SCHEMA_VERSION}, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    # -- Thesis / ThesisVersion -------------------------------------------------

    def add_thesis(self, thesis: Thesis) -> None:
        self.theses.append(thesis.thesis_id, thesis.to_dict())

    def add_thesis_version(self, version: ThesisVersion) -> None:
        if version.thesis_id not in self.theses:
            raise LedgerValidationError(
                f"ThesisVersion {version.thesis_version_id!r} references unknown "
                f"thesis_id {version.thesis_id!r}"
            )
        self.thesis_versions.append(version.thesis_version_id, version.to_dict())

    # -- AuditorRun / ReviewRound -------------------------------------------------

    def add_auditor_run(self, run: AuditorRun) -> None:
        if run.thesis_version_id not in self.thesis_versions:
            raise LedgerValidationError(
                f"AuditorRun {run.run_id!r} references unknown "
                f"thesis_version_id {run.thesis_version_id!r}"
            )
        self.auditor_runs.append(run.run_id, run.to_dict())

    def add_review_round(self, round_: ReviewRound) -> None:
        self.review_rounds.append(round_.review_round_id, round_.to_dict())

    def next_review_round_sequence(self, review_date_prefix: str) -> int:
        """Return the next free sequence number for round ids on a given date.

        ``review_date_prefix`` is the ``ER-YYYYMMDD`` portion; used by
        callers together with ``identifiers.make_review_round_id`` rather
        than computed inside that pure-function module.
        """
        existing = [
            rid for rid in self.review_rounds.ids() if rid.startswith(review_date_prefix + "-")
        ]
        if not existing:
            return 1
        return max(int(rid.rsplit("-", 1)[-1]) for rid in existing) + 1

    # -- ReviewCase ---------------------------------------------------------------

    def add_review_case(self, case: ReviewCase) -> None:
        if case.review_round_id not in self.review_rounds:
            raise LedgerValidationError(
                f"ReviewCase {case.case_id!r} references unknown "
                f"review_round_id {case.review_round_id!r}"
            )
        if case.run_id not in self.auditor_runs:
            raise LedgerValidationError(
                f"ReviewCase {case.case_id!r} references unknown run_id {case.run_id!r}"
            )
        if case.thesis_version_id not in self.thesis_versions:
            raise LedgerValidationError(
                f"ReviewCase {case.case_id!r} references unknown "
                f"thesis_version_id {case.thesis_version_id!r}"
            )
        self.review_cases.append(case.case_id, case.to_dict())

    # -- Adjudication (append-only, linear supersession) ---------------------------

    def current_adjudication_for_case(self, case_id: str) -> dict[str, object] | None:
        """Return the not-yet-superseded adjudication for a case, if any.

        ``None`` if the case has never been adjudicated. Raises if more
        than one un-superseded adjudication exists for the case -- that
        should be structurally impossible via ``add_adjudication``, so
        seeing it indicates ledger corruption, not a normal state.
        """
        superseded_ids = {
            a["supersedes_adjudication_id"]
            for a in self.adjudications.all()
            if a.get("case_id") == case_id and a.get("supersedes_adjudication_id")
        }
        candidates = [
            a
            for a in self.adjudications.all()
            if a.get("case_id") == case_id and a["adjudication_id"] not in superseded_ids
        ]
        if len(candidates) > 1:
            raise LedgerValidationError(
                f"case {case_id!r} has {len(candidates)} un-superseded adjudications; "
                "history is corrupted"
            )
        return candidates[0] if candidates else None

    def add_adjudication(self, adjudication: Adjudication) -> None:
        if adjudication.case_id not in self.review_cases:
            raise LedgerValidationError(
                f"Adjudication {adjudication.adjudication_id!r} references unknown "
                f"case_id {adjudication.case_id!r}"
            )
        current = self.current_adjudication_for_case(adjudication.case_id)
        if current is not None:
            current_id = current["adjudication_id"]
            if adjudication.supersedes_adjudication_id != current_id:
                raise LedgerValidationError(
                    f"case {adjudication.case_id!r} already has adjudication "
                    f"{current_id!r}; a new adjudication for this case must set "
                    f"supersedes_adjudication_id={current_id!r} to replace it, not "
                    "silently add another"
                )
        elif adjudication.supersedes_adjudication_id is not None:
            raise LedgerValidationError(
                f"Adjudication {adjudication.adjudication_id!r} sets "
                f"supersedes_adjudication_id but case {adjudication.case_id!r} has no "
                "current adjudication to supersede"
            )
        if (
            adjudication.supersedes_adjudication_id is not None
            and adjudication.supersedes_adjudication_id not in self.adjudications
        ):
            raise LedgerValidationError(
                f"Adjudication {adjudication.adjudication_id!r} supersedes unknown "
                f"adjudication_id {adjudication.supersedes_adjudication_id!r}"
            )
        self.adjudications.append(adjudication.adjudication_id, adjudication.to_dict())

    # -- Resolution / RegressionResult ---------------------------------------------

    def add_resolution(self, resolution: Resolution) -> None:
        if resolution.case_id is not None and resolution.case_id not in self.review_cases:
            raise LedgerValidationError(
                f"Resolution {resolution.resolution_id!r} references unknown "
                f"case_id {resolution.case_id!r}"
            )
        if resolution.case_id is None and resolution.policy_reference is None:
            raise LedgerValidationError(
                f"Resolution {resolution.resolution_id!r} must reference either a "
                "case_id or a policy_reference"
            )
        self.resolutions.append(resolution.resolution_id, resolution.to_dict())

    def add_regression_result(self, result: RegressionResult) -> None:
        if result.case_id not in self.review_cases:
            raise LedgerValidationError(
                f"RegressionResult {result.regression_result_id!r} references unknown "
                f"case_id {result.case_id!r}"
            )
        self.regression_results.append(result.regression_result_id, result.to_dict())

    # -- HistoryEvent ---------------------------------------------------------------

    _ENTITY_COLLECTIONS: dict[str, str] = {
        "Thesis": "theses",
        "ThesisVersion": "thesis_versions",
        "AuditorRun": "auditor_runs",
        "ReviewRound": "review_rounds",
        "ReviewCase": "review_cases",
        "Adjudication": "adjudications",
        "Resolution": "resolutions",
        "RegressionResult": "regression_results",
    }

    def record_history_event(self, event: HistoryEvent) -> None:
        collection_name = self._ENTITY_COLLECTIONS.get(event.entity_type)
        if collection_name is not None:
            collection = getattr(self, collection_name)
            if event.entity_id not in collection:
                raise LedgerValidationError(
                    f"HistoryEvent {event.event_id!r} references unknown "
                    f"{event.entity_type} id {event.entity_id!r}"
                )
        self.history_events.append(event.event_id, event.to_dict())
