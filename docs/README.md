# Documentation guide

Start with the [project README](../README.md) for use, the [development guide](DEVELOPMENT.md)
for checkout roles, and [reproducibility](REPRODUCIBILITY.md) for checks. The
[canonical deployment runbook](DEPLOYMENT.md) describes the release gates.
Use the [status snapshots](status/CURRENT_STATUS.md) to distinguish verified
source from deployed production. Private incident, operational, and reviewer
evidence belongs in institutionally approved restricted storage.

Use these entry points for the present system. Dated reports and plans are
retained as evidence of earlier decisions; read their dates before treating a
claim as current.

| Need | Start here |
|---|---|
| Dated deployment/validation snapshots and next evaluation task | [Current status](status/CURRENT_STATUS.md); verify live state before acting |
| Repository layout, worktrees, environments and artifact retention | [Development guide](DEVELOPMENT.md) |
| Direction and unresolved work | [Roadmap](ROADMAP.md) |
| Rule IDs, detector categories, and source metadata | [Rule architecture](RULE_ARCHITECTURE.md) and [rule inventory](rules/rule_inventory.md) |
| Local setup, CI, private gates, and packaging | [Reproducibility](REPRODUCIBILITY.md) |
| Hosted and local test scope, fixture boundaries, and CI limitations | [CI and private validation](CI_PRIVACY.md) |
| Service operation and rollback | [Deployment](DEPLOYMENT.md) |
| Local website development and read-only health checks | [Web UI guide](web_gui_mvp.md) |
| Recent rule corrections and regression locations | [Dated validation index](status/CURRENT_STATUS.md#recent-merge-and-regression-index) |
| Evaluation privacy, input provenance, and review labels | [Evaluation data](EVALUATION_DATA.md), [review labels](EVALUATION_REVIEW_LABELS.md), and [Ester judgment replay](ester_judgment_replay.md) |
| Published Windows installer / source pin | [rc.3 release record](releases/windows-0.2.0-rc.3.md) and [publication procedure](PUBLIC_WINDOWS_RELEASE.md) |
| Install or build the local app | [Desktop guide](implementation/offline_desktop.md) |
| Website/shared-source changes awaiting another installer | [Student wording](STUDENT_WORDING_USABILITY.md) and [About Us provenance](ABOUT_US_CONTENT.md) |
| Historical Linux validation | [2026-10-16 candidate](implementation/history/offline_desktop_linux_validation_20261016.md) |
| Product terminology | [Terminology](TERMINOLOGY.md) |

For prior research and implementation evidence, use the dated material under
[`evaluation/`](evaluation/), [`status/`](status/README.md),
[`planning/`](planning/), [`architecture/`](architecture/), and
[`implementation/`](implementation/). The
[`evaluation/ester_feedback/`](evaluation/ester_feedback/README.md) directory
contains historical reviewer packages and their format instructions; it is
not the status of the pending 19-PDF review. Do not move or delete those
artifacts based on age alone.
