"""Historical Ester feedback importers.

- ``authority_matrix``: rule-level policy, machine-parsed from
  ``docs/status/ester_authority_matrix_20260902.json``.
- ``xlsx_packages``: generic ``.xlsx`` review-package reader. Currently
  finds zero recoverable verdicts across the real repository (every
  package's ``Correct?``/``Notes`` columns are blank -- verified, not
  assumed); kept because a future returned package should be picked up
  without code changes.
- ``known_cases`` / ``case_migration``: hand-transcribed, case-level
  historical adjudications with real page/structural detail, and the
  logic that turns them into ledger records.
- ``known_policies``: hand-transcribed, rule-wide (not case-level) policy
  guidance sourced from a direct email/manual record rather than a
  sheet-tab finding row (e.g. R055) -- becomes a ``Resolution`` with
  ``case_id=None``, the same shape ``authority_matrix`` uses.
- ``thesis_registry``: maps the private corpus's short document names to
  ``Thesis``/``ThesisVersion`` records via a real SHA-256 content hash.
"""

from __future__ import annotations
