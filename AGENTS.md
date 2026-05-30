# Agent Instructions for njit-thesis-auditor

When working in this repository, act autonomously.

Default workflow:
1. Understand the task.
2. Make the needed changes.
3. Run validation:
   - python -m pip install -e ".[dev]"
   - ruff check .
   - mypy src
   - python -m pytest
4. Commit changes with a clear commit message.
5. Push the branch.
6. If the task says the branch is ready for PR, create the PR automatically.
7. If validation and checks pass, merge the PR with squash, delete the branch, pull latest main, and rerun validation.
8. Report the PR URL, latest main commit, and validation status.

Do not ask follow-up questions unless:
- the task is ambiguous in a way that could cause data loss,
- the task requires deleting or rewriting git history,
- credentials/secrets are needed,
- validation fails and the failure cannot be fixed safely.

For normal implementation, documentation, testing, PR creation, and squash merging, use the sensible default and continue automatically.

Do not modify raw guideline/data files unless explicitly requested.
Do not quote dissertation body text in docs or reports.
Do not commit generated reports unless explicitly requested.
