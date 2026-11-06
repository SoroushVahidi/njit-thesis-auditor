# Desktop PDF export supervision and publication (F2/F3)

Base: `b6d3dbbb247fe3722e19401ea09d37929419d180`, verified against remote
`main` on 2026-11-06. The integrated F1 receive guard is preserved.
This change addresses F2 and F3 only. It does not qualify or replace a released
Windows application, change audit policy, or deploy the hosted application.

## Reviewed contracts

The offline app shares the combined student-report, full-highlight and
single-page-highlight routes with the hosted app. Originally those asynchronous
routes rendered PDFs synchronously, outside the audit worker deadline. The
single-page plain fallback also rendered synchronously. Full and single-page
highlight writers saved directly to their final cache paths, and their routes
accepted file existence as cache validity.

The combined report already used a same-filesystem temporary directory and
atomic replacement. Its per-job lock and recheck addressed the prior concurrent
Windows WinError 5 problem: two requests must not both replace a report while a
downloader holds it open. That lock and hosted behavior are retained; highlight
routes now coordinate through the same per-job lock. Report contents, filenames,
geometry and successful download responses retain their existing contracts.

The original uploaded-PDF route only streams an existing file. The remaining
`/sample.pdf` route produces a fixed eight-page synthetic example. Desktop startup
now prepares that example before accepting HTTP requests; its route serves the
prepared bytes. Hosted sample generation is unchanged.

## F2 implementation

`PdfExportExecutor` supervises desktop PDF operations in a dedicated bounded
thread pool. Those threads perform process and file bookkeeping only, never PDF
rendering or PyMuPDF validation. Each operation invokes the established desktop
worker entrypoint in a separate process. The shared startup helper assigns the
existing `ProcessTree` containment before the owner opens the ready gate. The
worker applies the existing network restrictions before importing/running the
renderer. It uses the same source and frozen `--desktop-worker` command paths as
audits; there is no new multiprocessing bootstrap or worker listener.

Configuration is explicit through the executor constructor and app injection:

```python
exports = PdfExportExecutor(deadline=120.0, max_active=2)
app = create_offline_app(..., export_executor=exports)
```

Defaults are 120 seconds and two concurrent exports, independent of the existing
audit limits. The deadline starts at request acceptance and includes queue and
per-job-lock waiting. Expired queued operations never launch a worker. A separate
supervisor pool prevents a large export queue from starving the control thread
pool used by Quit and cancellation. Process-tree termination retains its existing
bounded stop/reap grace; `close()` waits up to five seconds for supervisors and
reports unsuccessful cleanup instead of claiming termination.

A client disconnect, HTTP-task cancellation, explicit Cancel, Delete, Delete all,
Quit, session expiry or application lifespan shutdown stops applicable exports.
The event loop remains available while supervisors render, wait and stop. Active
workspace leases exclude exports from retention/deletion. A failure to confirm
termination or remove staging retains ownership and the lease, sets the existing
cleanup warning, and permits a later Quit to retry. Worker crashes and deadlines
produce a safe retry notice rather than terminating the local server. The audit
job itself remains complete and usable. Child stdout/stderr and input-derived
exceptions are not exposed through server logs or notices.

Hosted rendering remains on its existing execution path. The desktop supervisor
is selected through offline app state; no hosted subprocess pool is introduced.

## F3 implementation

All three shared highlight/plain-page writers generate in a unique temporary
directory on the output filesystem. After the renderer closes its PDF handles,
validation checks the EOF terminator, successful unrepaired PDF opening, positive
page count and page-tree access. The validator closes its handles before
`os.replace`. Failure before creation, during save, validation or replacement
leaves an earlier output untouched. Permission, disk-full and Windows-style
sharing failures do not trigger deletion of the destination. Temporary directories
are cleaned on return or exception. Hosted highlight cache reads validate PDFs
rather than accepting existence, so a legacy truncated cache is regenerated.

Desktop workers render into private per-operation staging directories inside the
job workspace. All worker scratch space is directed there as well. A completion
manifest is written only after PDF validation and handle closure. The supervisor
confirms successful worker exit, stops/reaps remaining descendants, verifies the
artifact checksum, removes request/ready files, rechecks cancellation/deadline,
and atomically renames the staging directory into an immutable cache generation.
The manifest, PDF and combined-report metadata become visible together.

Cache keys include the operation, filters, complete job state, raw findings and
source identity. Cache reuse requires a completion manifest and matching PDF
checksum. Same-job requests serialize and reuse completed output. A changed
report gets a different generation, preserving downloads and old valid reports
if regeneration fails. A checksum-invalid generation is quarantined without
replacing an open file; it is removed with the job workspace. An original-PDF
fallback after failed full-highlight generation is not cached, allowing retry.

Cancellation and publication share a commit boundary. Cancellation accepted
before that boundary prevents publication. If it arrives after the rename, the
complete immutable artifact may remain cached, but an incomplete PDF is never
published. Windows sharing errors at rename return a safe failure and preserve
existing cache generations. No unlocked destination is removed to force success.

## Validation

All documents used here are synthetic. No private dissertation suite, installer
build, workflow dispatch, release publication or website deployment was performed.
No environment was reinstalled or repointed.

- Installed Linux stack: **547 passed, 1 skipped, 2 deselected**. The skip is a
  native Windows byte-range locking test. The two private sample-download cases
  were explicitly excluded, not executed. This includes desktop browser/session,
  security, F1 upload-budget, audit-worker lifecycle, retention, concurrent
  download, report, highlight-geometry and deterministic parity regressions.
  Versions: Python 3.12.3, FastAPI 0.136.3, Starlette 1.2.1, PyMuPDF 1.28.2,
  python-multipart 0.0.32 and ReportLab 4.5.1.
- Existing read-only desktop-pinned framework overlay: **540 passed, 1 skipped,
  2 deselected**, with FastAPI 0.143.2, Starlette 1.8.0 and OpenTelemetry API
  1.45.1. Per-command `PYTHONPATH` selected this overlay for the tests and export
  workers; telemetry auto-configuration was disabled. This repeats the installed
  selection except the seven browser/session cases, whose separate launcher
  helper intentionally resets `PYTHONPATH`. Those cases passed in the installed
  run. No dependencies were installed and no saved environment was changed.
- **50 new regression cases** exercise real short-lived Linux worker processes,
  responsiveness/heartbeat, disconnect/cancellation, timeout, worker failure,
  bounded concurrency and queue saturation, shutdown/deletion, retained ownership
  on stop failure, corrupt caches, concurrent readers/writers, partial output,
  publication failures, disk-full/permission errors and Windows-style sharing
  violations. Two existing privacy fault-injection tests now inject into the
  child process where rendering actually occurs.
- Direct baseline comparison against the base commit: **32 equivalent output
  pairs** across four rotations, cropped/uncropped pages and combined/full
  highlight/single-page highlight/plain-page exports. Extracted text, page boxes,
  rotation, drawings, annotations/styles, links, rendered-pixel hashes and report
  metadata match. Random PDF container IDs are not used as an output oracle.
- Source checks confirm unchanged detector/rule code, canonical rule data,
  thresholds, finding policy, evaluation/reference baselines and F1 body limiter.
- Ruff and mypy pass (160 source files). `git diff --check` passes.

Local validation commands and evidence are in the worktree's ignored
`.runtime/f2-f3-validation/` directory (`installed.log`, `installed.xml`,
`pinned.log`, `pinned.xml`, `pdf_parity.py`, `pdf-parity.json`). The installed and
pinned pytest invocations explicitly exclude `sample_audit_pdf_links` from
`test_highlight_pdf_student_routes.py`; no broad default pytest run is used.

## Native Windows qualification still required

Linux process tests and injected errors are not native Windows validation.
Before any later installer release, qualify the exact frozen application on a
supported native Windows host:

- Worker re-execution from the windowed PyInstaller executable, including paths
  with spaces/non-ASCII characters and runtime resource discovery. Static imports
  remain reachable from the existing bundled desktop worker; no spec/version or
  installer changes were made here.
- Ready-gate ordering, Job Object assignment (including nested-job environments),
  descendant termination/reaping, kill-on-close, failed-stop retry and no orphan
  workers during timeout, disconnect, Cancel, Quit and shutdown.
- NTFS directory rename and PDF replacement with browser downloads, antivirus and
  indexing software holding handles. Verify failure notices, retry, prior-cache
  preservation and cleanup of temporary directories under real sharing violations.
- User-profile ACL inheritance and access to private staging directories;
  low-space/permission failures; deletion while exports run or downloads hold
  handles. Inability to stop/delete must retain files and show the cleanup warning.
- Offline DNS/socket restrictions in export workers, windowed/no-console startup,
  responsive navigation/status/quit under simultaneous large exports, and frozen
  dependency compatibility. The Linux pinned overlay is not a complete frozen
  Windows dependency environment.

These are release qualification requirements. No native Windows success is
claimed, and this source branch must not be used to replace a released installer
without that separate qualification.
