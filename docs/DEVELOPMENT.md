# Development and repository organization

Start with the [README](../README.md) for application usage and the
[documentation guide](README.md) for specialist procedures. This guide describes
checkout and output conventions; it does not authorize cleanup, deployment or a
release.

## Checkout roles and main

Treat the live remote tip, a local branch, and the deployed revision as separate
identities. Check the current remote and worktree ownership before changing any
ref. Use an isolated checkout for changes. Disable LFS smudging before checkout
and keep restricted evidence outside public source and build outputs.

The authoritative upstream is the private
[`SoroushVahidi/njit-thesis-auditor`](https://github.com/SoroushVahidi/njit-thesis-auditor)
repository, whose default branch is `main`. A directory named `main` is not proof
that it has that branch checked out. Local `main` and `origin/main` can both be
stale. Inspect the repository and advertised remote state before choosing a base:

```bash
git remote get-url origin
git rev-parse --path-format=absolute --git-common-dir
git worktree list --porcelain
git branch --show-current
git rev-parse HEAD
git status --short
git ls-remote --symref origin HEAD refs/heads/main
```

In the shared project layout recorded in the November 2026 maintenance inventory,
the project container is not itself a Git checkout. Its `main/` child holds the
common Git administration directory but checks out a historical branch. The
`njit-thesis-auditor-clean-worktrees/live-current-main/` checkout is detached and
used by the production service. Neither is a general development workspace.
The private project notes record exact paths and SHAs; verify them before acting
rather than treating this description as a permanent host configuration.

Use an isolated task branch and worktree based on verified upstream main. Inspect
the existing worktree roles first. When a new worktree is authorized, choose an
unused branch and directory, check disk space and available inodes, and create it
from the verified commit. Confirm its HEAD, attachment and clean status. Record
the worktree path, base SHA, branch, resulting commit and PR in the task report.
Do not repurpose an existing checkout merely because its status is clean.

Preserve worktrees used by open PRs, running jobs, deployment, release provenance,
saved environments or historical evidence. Locked or dirty worktrees require
particular care. A merged PR does not establish that a local branch has no unique
commits, ignored evidence or path dependencies. Retirement needs a separate,
current dependency and recovery check; do not automatically remove a worktree
after pushing or merging.

## Paths and environments

Run setup and checks from the task worktree root. Use its `.venv/` for ordinary
development; `.venv-build/` is the documented isolated desktop build environment.
Follow [reproducibility](REPRODUCIBILITY.md) for Python versions, installation,
Git LFS and private validation prerequisites. Do not repoint or reinstall a saved
validation environment or the production environment for a maintenance task.

Editable installs can retain absolute source paths in `.pth` files. Saved
validation launchers, manifests, report generators and service configuration can
also depend on checkout paths. Before any later rename or relocation, check those
consumers, running processes and open PRs, preserve evidence and establish a
reversible replacement. A path can remain necessary after its process exits.
Leave uncertain dependencies in place.

For a local web session, use an available loopback port and a task-local runtime
directory; for example, from the task worktree with its environment activated:

```bash
NJIT_AUDITOR_WEB_RUNTIME_DIR="$PWD/.runtime/web_audits" ./scripts/run_web_gui.sh 127.0.0.1 8001
```

Check that the port is free first. Do not restart the shared production service
to test a documentation change. Desktop source development and its different
runtime-data location are described in the [desktop guide](implementation/offline_desktop.md).

## Source, outputs and retention

The [README layout](../README.md#repository-layout) maps the tracked directories.
In particular, `data/processed/` contains application metadata: its name does not
make it disposable. `docs/evaluation/`, `docs/status/` and other dated documents
preserve evidence, even when their procedures have been superseded.

| Location | Convention |
|---|---|
| `.runtime/` | Ignored task-local logs, temporary reports and web runtime output. |
| `results/` | Ignored root-level script output; may contain private extracted material. |
| `data/evaluation/generated/`, `data/evaluation/private/` | Ignored evaluation outputs and private inputs; retain according to the evaluation's evidence requirements. |
| `build/`, `dist/` | Ignored packaging output, including installers; published or provenance-bearing bytes require explicit retention. |
| Project-container `notes/<task>/` outside Git worktrees | Private task reports, run commands, logs and recovery records; not a public documentation destination. |

Use these established locations for new output instead of adding more scratch
directories. Keep approved durable engineering guidance in `docs/`; keep private
task evidence in private notes. Do not relocate existing output to conform to this
table without resolving its dependencies first. Ignored does not mean disposable,
and `.gitignore` does not protect an already tracked file. Review `git status` and
the staged diff before committing; do not force-add generated or private inputs.

Institutional specifications, student documents, reviewer records and derived
private reports must remain private. Public installer distribution is distinct
from source publication or a general public-engine split. Current main keeps the
generic machinery and NJIT-specific implementation in the same source package;
there is no standalone public-engine directory. Do not copy private rule
implementations, research data or repository history into public documentation or
a public engine. Follow the [privacy guidance](EVALUATION_DATA.md) and the desktop
publication allowlist; do not infer publication permission from file extensions,
LFS storage, ignored status or the existence of student-facing rule cards.

## Checks and review

For application changes, use the [standard checks](REPRODUCIBILITY.md#standard-checks-and-exact-commits)
and relevant synthetic tests. Private replay and browser coverage have additional
prerequisites in that guide; skips are not evidence that those checks ran.

For documentation-only work, inspect the complete diff, run `git diff --check`,
verify relative links (including anchors) and referenced paths, and run relevant
lightweight documentation checks. Do not launch a full application suite, install
dependencies or materialize private LFS inputs solely for prose edits. Confirm
that source, specifications, test expectations and release artifacts are unchanged.
Record what was checked and what was not; never inherit results from a different SHA.

The [status entry point](status/CURRENT_STATUS.md) is a dated snapshot, not a live
query of GitHub, running services or test jobs. Preserve historical results and
use observed state for new claims. Open a focused PR when requested; a passing
check does not itself authorize merging, deploying or deleting its worktree.

## Web and desktop releases

Use [deployment and rollback](DEPLOYMENT.md) for the user-level systemd service and
its dedicated deploy worktree. Its private runtime and review-ledger dependencies
must survive updates. Use the [desktop guide](implementation/offline_desktop.md),
[Windows smoke checklist](implementation/offline_desktop_windows_smoke.md) and
[publication procedure](PUBLIC_WINDOWS_RELEASE.md) for native builds and the limits
of qualification. The [rc.3 release record](releases/windows-0.2.0-rc.3.md) describes
immutable published bytes; newer source changes are not automatically in that
installer. Build, publication and deployment remain separate authorized tasks.
