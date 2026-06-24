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
Do not start P084 unless explicitly requested.
Do not change detector thresholds or rule IDs unless explicitly requested.
Do not pop or apply a git stash unless explicitly requested.

## Autonomous decision policy

When a task presents multiple possible implementation paths, choose the
recommended or safest path automatically instead of stopping for user
confirmation.

Default decision rule:
1. If one option is clearly recommended, choose it and continue.
2. If several options are possible, choose the smallest safe change that
   satisfies the task.
3. If a choice can be reversed later and does not affect user data,
   secrets, deployments, rule IDs, detector thresholds, or canonical
   guideline files, proceed without asking.
4. Record the decision and rationale in the final report.

Only ask the user before proceeding when the choice would:
- delete or overwrite user data
- apply or drop a stash
- close/delete branches or PRs
- change detector thresholds
- change rule IDs
- modify canonical rule JSON or raw guideline files
- expose private dissertation content or raw LaTeX
- deploy or restart services when not already authorized by the task
- require legal, policy, security, or personal judgment
- expand the task beyond the user's requested scope
- conflict with an explicit instruction from the user

Do not present options and wait for the user when you already know which
option you would recommend. Pick that option, proceed, and report what you
chose.
