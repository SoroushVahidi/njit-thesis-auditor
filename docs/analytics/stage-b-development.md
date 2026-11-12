# Stage B aggregate analytics development

This is an isolated, uncommitted implementation for review. Collection is disabled
by default. No merge, push, deployment, service change, release, production database
provisioning, or real-user collection was performed. Institutional activation approval
is **not established**. Stage A and the Stage A.5 implementation query remain the
specification; this document records implementation and executed evidence.

## Revision and scope

- Branch: `feat/analytics-stage-b-20261112`.
- Worktree: `/home/soroush/njit-thesis-auditor/worktrees/analytics-stage-b-20261112`.
- Remote main, implementation base and unchanged HEAD:
  `148599ccd516da534edab652f5f0da33d53f42f6`.
- Candidate identity: this HEAD **plus the uncommitted files listed below**. HEAD
  alone does not identify the implementation. A source/test digest is recorded below.
- Immutable comparison checkout: `../analytics-stage-b-baseline-20261112`, detached
  at the same baseline. Both checkouts exclude private documents and LFS fixtures.
- Stage A remains at `9591951e865815fb1ecad114bb3c6f86dfbe8e52`.
- PR #660 remains open/draft at `e92025305178f26d1a3bea01f67f18764582feef`;
  its checkout and production checkout have empty Git status. Neither was edited.
- Main did not advance; there are no unrelated baseline integration differences.

Created: `src/njit_auditor/analytics/{__init__,schema,store,collector,runtime,web,retention}.py`,
`tests/test_analytics_{schema,store,collector,web,retention,offline,failure_recovery}.py`,
and this document. Modified: `src/njit_auditor/web_app.py` and seven hosted-test
inventory entries in `.github/ci/tests.json`. No workflow or deployment file changed.

## Implemented behavior

The package import performs no analytics provisioning, connection, network request,
or thread start. Settings default to disabled and have no database-path default.
Only exact `NJIT_AUDITOR_ANALYTICS_ENABLED=1`, an explicit absolute
`NJIT_AUDITOR_ANALYTICS_DB`, the public web app, and
`NJIT_AUDITOR_WEB_ENVIRONMENT=production` request environment-based activation.
Offline application mode always takes precedence, including over an injected runtime
on the offline app. CLI has no collector startup path. Ordinary pytest/TestClient execution suppresses environment-driven startup, even
with inherited production flags; enabled synthetic tests explicitly inject an
`AnalyticsRuntime` and disposable store. Production settings were never changed.
Start and stop occur through application lifespan. Missing, incompatible or unsafe
storage makes analytics unavailable while the auditor continues.

The event types are frozen, slotted, closed scalar objects. Serialization revalidates
the exact event type and restricts envelopes to 256 bytes. Allowed data is schema
version, event kind, UTC date and, for a terminal event, completed/failed outcome and
bucket 0–7 or null for invalid timing. No job/document/request object enters the queue.

| Observation | Implemented boundary |
|---|---|
| Page view | Exactly one successful final ASGI body send of GET 200 HTML for `/`, `/help`, `/about`, `/rules`; independent of later background work. HEAD, redirects, errors, non-HTML, declared Purpose/Sec-Purpose prefetch and every other path are excluded. No route or query dimension is stored. |
| Accepted upload | After existing validation, registration and successful `BackgroundTasks.add_task`. Scheduling failure and rejected uploads do not count; repeated accepted submissions count separately. |
| Audit completed | After JSON, Markdown, view construction, Markdown preview, text output, `finished_at` and final in-memory `_set_job`. The earlier UI `complete` assignment is not sufficient. |
| Audit failed | Handled failure returns and exceptions observed before the existing wrapper swallows them; includes initial/final state updates and failures after early `complete`. |
| Duration | Monotonic time starts only after executor confirms the job exists. One terminal event supplies both its count and histogram contribution atomically, attributed to its terminal UTC day. |

Buckets are `[0,1)`, `[1,5)`, `[5,15)`, `[15,30)`, `[30,60)`, `[60,120)`,
`[120,300)`, `[300,infinity)` seconds. A bad duration preserves the terminal count,
omits the histogram increment, and degrades duration coverage. Duplicate terminal
notifications on an observation are ignored, including concurrent calls. Missing jobs,
process death and unobserved cancellation are unknown. Lazy PDF export failures do
not revise initial outcomes. Existing UI/error behavior, findings, thresholds and
`_after_audit_task` cleanup remain unchanged; in particular the pre-existing early
`complete` UI behavior is not repaired by this change.

## Store, writer and coverage

`initialize_database(path, epoch=..., activated_at=...)` is an explicit offline/test
provisioner. It requires an existing owner-only 0700 directory, creates one new 0600
file exclusively, and refuses overwriting. Epoch is a 32-character lowercase random
hex configuration identifier, not a student identifier. Normal startup only calls
`AggregateStore.open_existing` with SQLite URI `mode=rw`; there is no migration,
implicit directory creation, default database, backfill, or automatic reset.

Validation rejects relative/parent-traversing paths, symlink components and sidecars,
wrong ownership, non-0700/0600 modes, hard-linked database files, extended POSIX ACLs,
unsupported journals, and any schema difference including unexpected triggers/tables.
A nonblocking advisory file lock restricts cooperating collectors to one owner.
The writer uses DELETE rollback journal, FULL synchronous, 50 ms busy timeout,
secure deletion and in-memory SQLite temporary work. Its six tables are exactly
`schema_meta`, `daily_count`, `daily_duration`, `daily_coverage`, `committed_batch`,
`month_rollup`; no event, download, dashboard or administrative table exists.

Producers use a bounded nonblocking queue: 1,000 envelopes, with at most 100 events
in one immutable pending batch. Flush occurs at 100 queued events or within the
5-second writer cadence. The 60-second monotonic deadline is rechecked after
blocking storage boundaries, before individual batch writes, and before commit.
An already executing SQLite call cannot be interrupted safely; see the corrected
deadline guarantee below.
There is no disk spool. A random 128-bit nonce and aggregate deltas commit in one
`BEGIN IMMEDIATE` transaction. Counter overflow fails the entire transaction.
After an uncertain commit, reopening and checking the same nonce prevents replay
increments. Three storage failures open a 60-second breaker, stop enqueueing, and
allow one recovery attempt per interval. Static diagnostic codes and bounded loss
state contain no payload or exception text. Loss snapshots preserve up to 92 UTC
dates; a separate 1,000-entry date-only mailbox preserves notifications when the
snapshot lock is busy. Producers use nonblocking acquisition/enqueue and never do
storage I/O. Mailbox/date-cap exhaustion retains persistent uncertainty; successful
persistence acknowledges its notification so it does not trigger work on every tick.
Persistent uncertainty is carried by ordinary scheduled heartbeats until restart.
Failed persistence restores the snapshot without replacing concurrent notifications.

`known_dropped` is a coalesced presence lower bound for loss/invalid-observation or
unlocalized quality-loss evidence, **not an exact count of missing events**. New
known evidence sets a daily component's floor to 1 via `MAX(existing, 1)`;
uncertainty alone preserves its existing floor. Repeated persistence, ambiguous
commits and reconnects cannot increment the same evidence again. Larger pre-existing
values are preserved, not migrated or reconstructed. The process-local `dropped`
diagnostic also remains a lower bound under contention. Shutdown joins for no more
than one second; best-effort final persistence runs only on the writer thread, which
can outlive that wait if storage blocks.

Nonces have a 47-hour-59-minute deadline, leaving one heartbeat interval inside the
48-hour retention ceiling during healthy operation. They are pruned on heartbeat
and retention maintenance. Retry lifetime remains only 60 seconds. This is **not
end-to-end exactly-once delivery**: RAM, startup, queue, crash and storage losses can
undercount. No counts are reconstructed from job deficits or documents.

Writer heartbeats initialize four daily counter cells and sixteen histogram cells
on active days, including idle days. Coverage is independent: an open day starts
partial; only a continuously healthy whole day becomes observed. Before a heartbeat
advances, any unsettled observations for a prior date conservatively keep that date
and its monthly coverage partial, even if those observations later commit. Restart
includes two dates preceding the last heartbeat (bounded by activation and retention),
because producers accept current/previous UTC dates and queues can cross midnight.
Older unsettled dates are already degraded before a heartbeat advances. Startup/restart,
missed heartbeats and wall/monotonic discrepancies conservatively downgrade coverage.
Missing days have unavailable coverage without fabricated count zeros. Quality loss
is not erased by successful retry. A later clock loss can downgrade a closed month's
coverage without recomputing or incrementing its once-only totals.

Monthly totals are formed once per `(epoch, month)`, no earlier than month end plus
48 hours. Missing days make a month unavailable. Daily cells expire 90 days after
day end; monthly rows expire 24 months after month end. Rollup and raw expiry are
separate transactions. Initialization, rollup and optional unavailable-marker writes cannot prevent an
independent deletion-only expiry attempt, including SQLite FULL aborting a transaction.
Failed heartbeat initialization triggers expiry even after maintenance earlier that day; absence of a monthly row means unavailable. No reader/publication
API is provided: a future consumer must select daily **or** monthly coverage for a
period, never sum overlapping representations or treat unavailable placeholders as
measured zeros. Original expiry is never reset on reopen.

## Reproducing the synthetic validation

Use the isolated development checkout and an isolated environment. Do not run these
commands in production. The completed environment was installed with:

```bash
python3 -m venv --system-site-packages .venv
uv pip install --python .venv/bin/python -e '.[dev]'
```

No saved or production environment was reinstalled. Versions used were Python 3.12.3,
SQLite 3.45.1, FastAPI 0.162.5, Starlette 1.10.0, PyMuPDF 2.1, pytest 9.2.0,
Ruff 0.16.10 and mypy 2.4.1. Baseline and candidate subprocesses use the same dependency
environment, with separate source paths. This is not a qualification of every
production dependency combination or the published Windows executable.

Full executed selection (the two read-only evidence variables require the explicitly
prepared/authorized local checkouts; ordinary CI skips those unavailable prerequisites):

```bash
export ANALYTICS_BASELINE_ROOT=/home/soroush/njit-thesis-auditor/worktrees/analytics-stage-b-baseline-20261112
export ANALYTICS_PRODUCTION_ROOT=/home/soroush/njit-thesis-auditor/njit-thesis-auditor-clean-worktrees/live-current-main
export ANALYTICS_BENCHMARK_RESULT="$PWD/.runtime/stage-b-validation/performance.json"
.venv/bin/python -m pytest -q \
  tests/test_analytics_schema.py tests/test_analytics_store.py \
  tests/test_analytics_collector.py tests/test_analytics_web.py \
  tests/test_analytics_retention.py tests/test_analytics_offline.py \
  tests/test_analytics_failure_recovery.py \
  tests/test_web_app.py tests/test_web_retention_sweeper.py \
  tests/test_offline_desktop.py tests/test_desktop_network.py \
  tests/test_desktop_executor.py tests/test_desktop_upload_budget.py \
  tests/test_upload_handling.py tests/test_about.py tests/test_help_rules.py \
  --junitxml=.runtime/stage-b-validation/results.xml
.venv/bin/ruff check .
.venv/bin/mypy src
git diff --check
```

The final results and candidate digest are recorded below. Detailed local synthetic
logs and JUnit output are in the ignored `.runtime/stage-b-validation/` directory.
Inventory validation compared Git-tracked test/support paths plus the seven new
modules against the unchanged classification rules: 216 hosted modules, with only
seven necessary additions. The normal whole-checkout inventory command cannot be
used verbatim in this deliberately sparse worktree because unrelated nested test
sources are absent; no inventory assertion or workflow was weakened.

## Mandatory acceptance gates

All gates refer to baseline `148599ccd516da534edab652f5f0da33d53f42f6` and this
uncommitted candidate. Each named test was included in the full command above.

| Gate | Executed evidence and assertions | Result |
|---|---|---|
| 1: disabled equivalence | `test_immutable_baseline_differential`: separate baseline/candidate subprocesses, same generated PDF bytes, informational/health/error responses, rejected upload, successful audit, handled failure, text-write failure after early complete and final state-update failure. Exact report/findings, job outcome, response and cleanup equality. `test_disabled_import_and_lifespan_no_boundary` instruments database/collector/thread/network boundaries. | PASS |
| 2: enabled correctness | `test_exact_enabled_sequence_and_utc`: injected temporary SQLite runtime, four page responses, two accepted submissions, one completed audit in bucket 2 and one failed audit in bucket 1 across UTC month midnight. Rejection/prefetch/HEAD excluded. Other schema/store/web tests cover all eight boundaries, duplicate notification, concurrent terminals, repeated submissions and nonce retries. | PASS |
| 3: failure isolation | `test_audits_reports_cleanup_survive_fault`: ten faults, each with an otherwise successful audit and a handled failed audit; exact comparison to disabled reports/findings/outcome/cleanup. Missing, readonly, full, corrupt, transaction, overflow, blocked writer, terminated writer, lock contention and bad clock. `test_real_sqlite_readonly_and_full` additionally exercises actual SQLite readonly/full errors; ambiguous commit and before/after-commit subprocess crash tests preserve atomic count/histogram and nonce behavior. Helper/report/final-state failure tests preserve cleanup. | PASS |
| 4: desktop/CLI isolation | `test_real_cli_inherited_flags` runs the actual CLI module on a generated PDF. `test_real_desktop_launcher_inherited_flags` runs the real launcher, Uvicorn loopback server, session/CSRF upload and actual desktop worker subprocess through shutdown. All inherit enable=1, production environment and a nonexistent temporary DB-path trap. Instrumentation in parent and worker asserts no analytics open, emit, writer start/thread or analytics network connection; report findings and upload cleanup succeed. Only GUI/browser presentation is replaced by the synthetic HTTP driver. | PASS |
| 5: no production collection | `test_production_baseline_readonly_metadata`: source HEAD and clean tracked diff, analytics package absent, active user systemd service's PID/working directory, process environment filtered locally for analytics keys, unit/drop-in absence of those keys, `/version` baseline/production identity, proposed production analytics directory absent. No sensitive log or document content read. Combined with default-off/import/lifespan tests. Claim concerns this subsystem on the recorded service, not existing access logs or unknown external infrastructure. | PASS |
| 6: rules unchanged | `test_rule_and_threshold_hashes_unchanged`: baseline Git blob hashes match every existing source/resource file except the intentionally modified web adapter, plus `data/processed/rules`. Includes detector implementations, shared thresholds/helpers, `specs`, findings models, templates and report code. Gate 1 independently checks synthetic report/findings equality. | PASS |

Differential normalization is limited to the report metadata `generated_at` value,
the Markdown `Generated at` line, and actual `created_at`/`finished_at` values in
web responses. Both processes use the same fixed synthetic job ID, basename and
temporary directory, avoiding path/ID normalization. No finding, rule, threshold,
severity, substantive report text or cleanup result is normalized. `/version` is
verified separately for production, not normalized into the output comparison.
A finite synthetic suite cannot prove equivalence for every possible input.

Corrections made during validation: a test fixture's Starlette State restoration,
a missing benchmark import, required sparse packaging source files, and the
retention case where an unavailable-month marker itself cannot be written. The
last case now expires raw data independently and has a regression test. Existing
test assertions and application rule/report behavior were not weakened.

## Limits, future integration and rollback

- This implementation remains disabled and uncommitted. No real-user analytics data,
  private fixture, dissertation, personal identifier or production analytics database
  was collected or created. Tests generate PDFs and disposable SQLite files only.
- This is Linux source qualification: permission/ACL checks and the advisory lock use
  POSIX/Linux facilities. Desktop/CLI never open analytics, including in the inherited-
  flag subprocess tests. No native Windows build or GUI/browser automation was run.
- The full private/manuscript replay suite was intentionally not run. Published desktop
  releases, installer assets, links, production dependencies and release settings are
  unchanged. No dashboard, CSV, download collector, public endpoint or telemetry was added.
- Proposed timing targets are measurements, not guarantees. The short benchmark cannot
  establish a stable sub-1% audit regression; all measured runs are disclosed below.
- Retention runs while the writer and storage are available. A stopped process,
  uninterruptible filesystem call, denied writes or corrupt storage cannot physically
  guarantee deletion at a deadline. Recovery keeps original cutoffs and expires overdue
  rows. Secure-delete/DELETE journaling do not promise physical SSD erasure or remove
  external backups. A separately authorized retention/storage operating policy is needed.
- One cooperating writer, no publisher/live reader, no distributed delivery guarantee,
  no persistent event spool. Quotas and an independent audit disk reserve are activation
  prerequisites. The controlled storage directory must be outside deploy, upload,
  report and desktop roots; ownership validation is not a substitute for that provisioning
  decision or protection against a malicious same-UID/root operator.
- Queue expiry, breaker, writer death and startup can undercount. Diagnostics/known-loss
  markers are conservative, bounded lower-bound evidence, not reconstruction of lost
  student activity. Idle zeros require the associated coverage state.
- Future activation requires institutional purpose/notice/retention decisions, single-
  process deployment review, exact-runtime qualification, dedicated ownership/permissions,
  quotas, backup exclusions, access-log/diagnostic review and explicit deployment approval.
  No named person's approval is inferred. Separate dashboard/publication/download stages
  remain separate work.

Rollback is source-only removal/reversion of this isolated change after preserving
review work as needed. There is no migration or production action to undo. The baseline
ignores separate analytics storage. Do not reset totals, downgrade a database, replay
jobs, restore raw history, change upload retention, or touch PR #660 as a rollback.
If a later activation is authorized, disabling the sink precedes its separately reviewed
service rollback; this document does not authorize that future deployment.

## Pre-correction validation record (superseded)

The original implementation reported **COMPLETED_SUCCESS** before independent
review identified H1–H3 and M1–M3. That readiness claim and the original benchmark
methodology are superseded by the correction record below.
Recorded 2026-11-12T14:28:07.501059+00:00.
Final selection: **635 passed, 0 failed, 0 skipped** in 45.36 seconds:
168 new analytics tests and 467 existing synthetic regressions.
Ruff: **all checks passed**. Mypy: **no issues in 165 source files**.
`git diff --check`: passed. Three existing/dependency warnings concern the fitz alias,
Starlette TestClient/httpx, and a deliberately duplicate synthetic ZIP member.
No production logs or student documents were consulted to resolve a test.

Candidate source/test/inventory SHA-256: `7fd0e46dd196be0d341db3c8bbe5525646b689229df4cd7190f1f1e0254cb0f3`.
Computed from sorted `relative_path + NUL + file_sha256 + newline` records for the
16 implementation/test/inventory files. The self-referential documentation and
ignored generated artifacts are excluded. Per-file hashes are in
`.runtime/stage-b-validation/candidate.json`; HEAD remains the baseline and no
implementation commit was created.

Benchmark host: Linux x86_64, Intel Core i7-12700K, kernel 7.0.0-29-generic.
Each short isolated subprocess measured 1,000 producer calls and 60 paired generated
PDF audits after five warm-up pairs, alternating order using a fixed random seed.
The enabled case uses the actual background SQLite writer. Queue limit is 1,000;
final traced allocation peak was 259,475 bytes. RSS is a process-level before/after
measurement and includes thread/SQLite overhead; it is not a universal maximum.

| Run | Producer p95 ms | Added RSS MiB | Disabled audit p95 ms | Enabled audit p95 ms | p95 change |
|---|---:|---:|---:|---:|---:|
| First isolated run | 0.026721 | 0.547 | 4.045883 | 4.037062 | -0.218% |
| First combined run | 0.024946 | 0.824 | 4.050518 | 4.152280 | +2.512% |
| Final candidate run | 0.027603 | 0.848 | 3.966400 | 4.000665 | +0.864% |

The original sample reported meeting the proposed producer <2 ms, added RSS <32 MiB
and audit p95 <1% targets. Its disabled measurements incorrectly ran with an active
analytics writer, so these audit comparisons do not qualify the corrected implementation. The earlier +2.512% sample means a stable sub-1% audit regression
is **not established**. No statistical significance or large-document/load guarantee
is claimed, and no timing threshold was weakened to obtain a functional pass.
Longer performance qualification belongs to a separately bounded future validation.

Final remote-main verification still returned the baseline SHA. Final PR #660 metadata
still showed open/draft with head `e92025305178f26d1a3bea01f67f18764582feef`.
Production/PR worktree status remained empty. No deployment, push, merge, activation,
release, existing-worktree cleanup or production configuration mutation occurred.
Next action: independent review of this isolated uncommitted change; institutional
and operational activation gates remain separate and unresolved.


## First independent-review corrections, 2026-11-12 (historical)

The initial source/test/inventory digest was recomputed before edits and matched
`7fd0e46dd196be0d341db3c8bbe5525646b689229df4cd7190f1f1e0254cb0f3`, including
all 16 individual file hashes. HEAD and the branch remain unchanged. The original
inventory, schema, web observation helpers and failure-recovery module were preserved.
All corrections remain uncommitted. No production provisioning or configuration,
private documents, rule/threshold changes, release actions or PR #660 edits occurred.

The supplied review findings were reproduced directly from the implementation.
A separate detailed reviewer reproduction artifact was requested but was not available
in the task materials. The January 2/3 regression explicitly establishes continuous
January 2 coverage, enqueues at 23:59 UTC, and expires the event at January 3 00:00 UTC;
it also covers pending retry, reconnect and breaker variants.

| Finding | Root cause and correction | Focused regression evidence |
|---|---|---|
| H1 | Daily allocation ran before maintenance, so SQLite FULL prevented deletion. Heartbeat now attempts maintenance in `finally`; deletion is its own transaction, independent of initialization, rollup and marker allocations. Failed initialization also retries expiry within the same day. | `test_full_database_initialization_cannot_block_expiry` fills the real daily B-tree using `PRAGMA max_page_count`, confirms `_initialize` raises SQLite FULL, then verifies deletion of expired counters, durations, coverage and nonces despite the heartbeat error. Today's cells fit after deletion; full heartbeat recovery succeeds after capacity restoration. `test_failed_initialization_retries_expiry_within_same_day` checks nonce expiry. |
| H2 | A Boolean loss flag discarded original event dates and could downgrade January 3 while January 2 stayed observed. Every queued/pending/breaker loss now carries its original UTC date; both daily components and any existing monthly row are downgraded without recounting totals. | Four `test_january_second_loss_at_third_midnight` cases exercise queue, pending, reconnect and breaker losses. They assert zero fabricated counts, January 2 uncertainty and a downgraded existing monthly row with unchanged totals. |
| H3 | Separate read/reset of shared loss state could erase concurrent producer overflow. A lock now protects snapshot exchange; producers use nonblocking acquisition with a never-cleared bounded uncertainty fallback. Failed heartbeats restore snapshots alongside newer losses. | `test_concurrent_overflow_during_loss_consumption` forces producer overflow between snapshot read and clear while the writer holds the lock; the producer finishes before lock release and its uncertainty survives. `test_loss_snapshot_restored_when_heartbeat_fails` verifies both old/new dates survive. |
| M1 | The writer reused an entry monotonic timestamp across blocking calls. It now refreshes after open/heartbeat, checks before/after nonce lookup, and passes a deadline guard into each batch transaction boundary. Expired uncommitted work rolls back and degrades its original dates. | Six `test_expiry_after_blocking_storage` cases delay open, heartbeat, lookup, BEGIN, nonce insertion and count insertion. Each leaves zero counters/histograms/nonces and records uncertainty. `test_commit_crossing_deadline_preserves_atomic_counts_and_marks_loss` covers the unavoidable already-running COMMIT case. |
| M2 | Public-web/production environment checks did not distinguish test execution. Lifespan now suppresses environment activation when pytest, Starlette TestClient or pytest's current-test marker is present. Explicit synthetic runtime injection remains supported; offline precedence remains unchanged. | `test_ordinary_testclient_inherited_production_flags` runs outside pytest with its marker removed, inherits all production flags, and traps open/start/emit/thread/network boundaries. `test_testclient_allows_explicit_synthetic_runtime` verifies a disposable injected writer persists exactly one page view. Existing real desktop/CLI inherited-flag tests are rerun. |
| M3 | Disabled samples shared a live enabled writer and one short paired run hid variability. Five bounded paired trials now use ten separate subprocesses; each has five warmups and 60 measured audits. Disabled processes assert no analytics file or writer; enabled processes use the real SQLite writer. Trial order is reproducibly randomized. | `test_short_synthetic_performance` records every audit sample, per-trial median/p95/standard deviation, producer median/p95, allocation/RSS and between-trial p95 differences. Existing producer/memory assertions remain intact; audit overhead is reported without a sub-1% pass assertion. |

The privacy regression now sends `PRIVATE_CANARY` in forbidden filename/text fields
through `BoundedCollector.emit`, proves rejection and an empty queue, then flushes a
valid observation and scans every remaining storage file for the sentinel. The exact
six-table allowlist and no-payload-log assertions remain in place.

### Retention and deadline guarantees

Daily expiry remains 90 days after day end, monthly expiry 24 months after month end,
and nonce expiry retains the original 47-hour-59-minute deadline. No recovery resets
these cutoffs. Late loss never recreates expired daily coverage solely to mark loss;
retained monthly confidence can still be downgraded. Rollup counts remain once-only.
Allocation failure is surfaced after the independent expiry attempt; deletion success
is not misreported as successful initialization. SQLite FULL can abort a whole
transaction, which is why optional marker insertion no longer shares expiry's transaction.

A batch that expires before its next operation is rejected/rolled back. An SQLite
statement or COMMIT that already started can finish after the deadline: cancellation
cannot safely promise rollback of an ambiguous/durable commit. After such a commit,
counts and nonce remain atomic, replay is avoided, and the writer records coverage
uncertainty for the original dates. This is a boundary-check guarantee, not a hard
wall-clock upper bound on an executing filesystem call. Process suspension/death,
corruption, denied writes and storage stalls still prevent physical deadline guarantees.

### First-correction validation and performance record (superseded)

This candidate reported **COMPLETED_SUCCESS** before independent rereview exposed
the remaining shutdown/restart and sticky-loss defects. That readiness assessment
is superseded by the final targeted-correction record below.
Recorded 2026-11-12T20:07:12.117129+00:00.
Final selection: **653 passed, 0 failed, 0 skipped** in 69.99 seconds, comprising
**186 analytics tests and the unchanged 467 existing synthetic regressions**.
Eighteen focused regression cases were added; the privacy canary and benchmark were
strengthened in place. Ruff passed; mypy passed for 165 source files; `git diff --check`
passed. The same three pre-existing/dependency warnings remain.

Corrected source/test/inventory SHA-256:
`e7bf0d5f4f4b89a025ac56807a6fc97bcc50213245a324f8ce4ca40def71fc34`.
The digest uses the original 16-file algorithm and excludes this document/artifacts.
The per-file hashes, raw trials, JUnit, logs and gate-to-test mapping are retained in
`.runtime/stage-b-corrections/{candidate.json,performance.json,results.xml,pytest.log,ruff.log,mypy.log,gates.json}`.
The original `.runtime/stage-b-validation/` evidence remains intact.

| Gate | Current executed evidence | Result |
|---|---|---|
| 1 | Immutable baseline differential and instrumented disabled import/lifespan passed; reports/findings/responses/cleanup match under the existing timestamp-only normalization. | PASS |
| 2 | Exact enabled UTC sequence, all bucket/schema/store tests, idle/retention/rollup tests and the new H1/H2/H3/M1 regressions passed. | PASS |
| 3 | All audit/report/cleanup fault combinations, actual SQLite readonly/full, ambiguous nonce retry, recovery and crash tests passed. Initialization failure still expires writable data and capacity restoration permits recovery. | PASS |
| 4 | Actual CLI and desktop launch/worker tests passed with inherited production flags; ordinary non-pytest TestClient startup reached no analytics boundary. Explicit disposable test injection counted exactly one view. | PASS |
| 5 | Read-only production metadata test passed: original baseline HEAD, no analytics source/package or production database directory, no analytics process/unit flags, unchanged active service source/version. Candidate remains default-off and uncommitted. | PASS |
| 6 | Original source/resource/rule blob hashes passed; disabled differential preserved findings and JSON/Markdown/text reports. No rule, threshold or detector edits. | PASS |

PR #660 was read only: still open/draft at
`e92025305178f26d1a3bea01f67f18764582feef`; its checkout is clean.
No commit, push, merge, deployment, activation or production configuration write occurred.

The final corrected benchmark used five trials per mode, five warmup audits and
60 measured generated-PDF audits per subprocess (300 measured audits per mode).
All disabled trials asserted writer/database absence. Each enabled trial measured
1,000 producer calls after 100 warmups. Trials ran in reproducibly randomized order.
The producer <2 ms, RSS <32 MiB and traced-allocation <32 MiB assertions all passed.
The maximum traced allocation peak was 265,121 bytes.

| Trial | Disabled median / p95 ms | Enabled median / p95 ms | p95 change | Producer p95 ms | Added RSS MiB |
|---|---:|---:|---:|---:|---:|
| 1 | 3.848553 / 3.922605 | 3.943744 / 4.076659 | +3.927% | 0.023757 | 0.477 |
| 2 | 3.976133 / 4.109324 | 3.917091 / 4.103312 | -0.146% | 0.029352 | 0.820 |
| 3 | 3.851285 / 3.939797 | 3.940241 / 4.218376 | +7.071% | 0.024312 | 0.809 |
| 4 | 3.844303 / 3.891069 | 3.946692 / 4.623590 | +18.826% | 0.025777 | 0.812 |
| 5 | 3.852056 / 3.912667 | 3.929289 / 4.642966 | +18.665% | 0.074136 | 0.816 |

Median paired-trial p95 change: **+7.071%**;
range **-0.146% to +18.826%**;
between-trial standard deviation **8.672 percentage points**.
Individual audit sample arrays and per-trial standard deviations are in `performance.json`.
This spread is descriptive uncertainty, not a confidence interval. Five short trials
on one host and tiny generated PDFs do not establish consistently sub-1% overhead,
large-document performance or loaded-service behavior. The earlier corrected run
before the final COMMIT-boundary/future-date checks reported median +3.659%, range
+2.662% to +21.516%; it is preserved as `performance-before-commit-boundary.json`.
The original shared-writer baseline numbers above are superseded, not supporting evidence.

Remaining risks are the documented inability to cancel executing storage calls or
physically delete on unavailable storage, conservative persistent coverage uncertainty
after bounded loss-state contention, and unqualified performance across real workloads.
The future-date rejection regression ensures a rejected input cannot create long-lived
future coverage rows. No broad private-document or production load validation was run.

**Historical integration assessment (superseded):** ready for independent rereview.
The rereview required the two targeted corrections recorded below. This was not
deployment/activation readiness: the sub-1% performance target
is not established, and the institutional/storage/operational prerequisites above
remain separate. No additional performance project or production action was started.


## Final targeted H2/H3 corrections

The reviewed candidate digest was verified before edits:
`e7bf0d5f4f4b89a025ac56807a6fc97bcc50213245a324f8ce4ca40def71fc34`.
Independent reproduction artifacts were available in
`/tmp/njit-stage-b-rereview-1tz_0rac/`. Their unchanged reproduction script was run
before and after these corrections. Evidence, reviewed-source copies and diffs are
retained separately in `.runtime/stage-b-final-corrections/`; earlier evidence was
preserved. Functional changes are confined to collector, retention and store loss
handling. Runtime activation, web adapters, schema/DDL, inventory, rules and reports
are unchanged from the reviewed candidate.

### Root causes and corrections

H2: the writer discarded its remaining queue/pending batch during teardown without
persisting their original dates. Startup recovery began at the last heartbeat's day,
which could already be January 3 while January 2 observations remained in RAM.
The writer now records discarded dates and applies their coverage downgrade in the
same best-effort shutdown transaction as the clean-shutdown flag. It does not invent
counter/histogram increments for discarded work. A heartbeat also snapshots bounded
queue/pending dates and downgrades unsettled prior dates before advancing durable
heartbeat metadata. This protects older backlog even if the process later dies.
Restart conservatively includes the preceding two dates and downgrades intersecting
existing monthly coverage without changing its totals. Two dates cover the allowed
previous-day event timestamp plus a midnight queue crossing. No missing-day count
zeros are fabricated.

H3: lock contention discarded the known UTC date into a permanently sticky Boolean.
That Boolean was treated as a new loss at both heartbeat checks on every writer tick;
coverage persistence incremented `known_dropped` each time. The correction retains
dated contention notifications in a bounded mailbox, separates new pending loss from
acknowledged persistent uncertainty, and persists the coalesced presence marker
idempotently. The saturation acknowledgement advances only after successful
persistence; failures restore pending evidence while leaving concurrent notifications
intact. Periodic uncertainty propagation never manufactures additional known losses.
No new tables, schema version, event identifiers or per-document records are needed.

| Original independent reproduction | Before | After |
|---|---|---|
| 200 events immediately before midnight; first batch commits 100; shutdown discards 100; restart | January 2 `observed`, marker 0, only 100 persisted | January 2 already `partial` before teardown, then `unavailable` with marker 1 after restart; exactly 100 persisted |
| One overflow during snapshot-lock contention, followed by ten idle ticks | 20 transactions; marker 40 → 80 | 0 transactions; marker 1 → 1 |
| Real SQLite FULL initialization/expiry control | Expired writable rows deleted | Same; H1 remains corrected |

### Focused regression coverage

Twenty-one cases were added without changing existing assertions:

- Eight shutdown/restart/monthly cases cover before midnight, after midnight,
  mixed-date queues, a pending failed batch, shutdown write failure, process death
  without finalization, mixed-date shutdown failure and an after-commit shutdown error.
  Each forms a monthly rollup and checks uncertainty, exact retained event counts and
  once-only totals.
- One contended overflow verifies producer return while the writer owns the lock,
  exactly 1,000 accepted counts, marker 1, and zero transactions over ten idle ticks.
- A contention/midnight case proves the original date is marked, not the new day.
- Three loss-persistence cases inject failure before commit, after commit and during
  maintenance following a successful commit, then reconnect and retry.
- Concurrent notification during persistence and saturation during snapshot clearing
  both preserve newly pending evidence. The original forced-interleaving test remains.
- Mailbox saturation has one notification, no idle transactions after persistence,
  and one ordinary heartbeat when 60 seconds pass, with unchanged markers.
- Breaker recovery retains loss without fabricating event counts; uncertain saturation
  commits cannot acknowledge unpersisted state.
- A blocked shutdown write verifies the original join budget; explicit retention
  tests preserve larger existing marker values and downgrade existing monthly coverage
  without recounting.

### Guarantees and unavoidable limits

The unchanged `stop()` budget limits the caller's wait to at most one second; it does
not promise that an already-running SQLite call or final writer transaction completes
within that interval. The request-processing thread performs no analytics disk I/O.
If final persistence fails or the process dies, restart conservatively lowers coverage
using durable heartbeat metadata and the dates already marked uncertain while queued.
A stopped/dead process cannot update its database until recovery. Consumers must not
interpret stale coverage from an unavailable collector as proof of a complete live
period; no public reader or publication endpoint exists in Stage B.

RAM observations are not durable and are never reconstructed. Actual loss counts are
unknown after process death, ambiguous commits or bounded-state exhaustion. The
presence marker deliberately does not estimate that volume; multiple incidents on
one day may still leave it at 1. An unlocalized quality-loss notification marks the day
it is recorded; other potentially affected retained days/months are downgraded without
inventing per-day lost-event counts. Existing larger diagnostic values are preserved;
these corrections do not retrospectively repair earlier databases or migrate storage.
Conservative restart/backlog uncertainty can lower coverage even when no event was
ultimately lost. Original retention cutoffs, event deadlines and nonce deadlines are
unchanged; denied writes, corruption and stalled storage still prevent physical
retention/deletion guarantees.

### Final verification and performance

Status: **COMPLETED_SUCCESS** for the two requested corrections and six gates.
Recorded 2026-11-12T20:48:44.341699+00:00. Final source/test/inventory SHA-256:
`99756e240f47f36f1f81ec12975de79bdd5622369a5055406a7396cf65be8b36`.
The digest retains the original sorted 16-file algorithm; documentation and generated
artifacts are excluded. Per-file hashes are in `candidate.json` in the final evidence
directory. Only three analytics source files and two existing test modules changed
relative to the reviewed candidate, plus this document. AST comparison verified that
every pre-existing function in the two edited test modules is unchanged.

The final selection passed **674 tests, 0 failed, 0 skipped**, in 71.81 seconds:
**186 existing analytics cases + 467 existing synthetic regressions + 21 new cases**.
All 653 reviewed test identities remain present. Ruff passed; mypy passed for 165
source files; `git diff --check` passed. The same three existing/dependency warnings
remain. JUnit, pytest/Ruff/mypy logs, before/after reproductions, privacy-canary output,
per-file hashes and the gate-to-test mapping are retained in
`.runtime/stage-b-final-corrections/`.

| Gate | Executed supporting evidence | Result |
|---|---|---|
| 1 | `test_immutable_baseline_differential` and instrumented disabled import/lifespan checks; original reports/findings/responses/cleanup match under the existing timestamp-only normalization. | PASS |
| 2 | Exact enabled UTC sequence and all prior retention/coverage tests; eight shutdown/restart/monthly cases; dated concurrent notifications; idempotent retry before/after commit and following maintenance failure; saturated mailbox, breaker recovery and idle transaction assertions. Both independent reproductions now give the corrected results above. | PASS |
| 3 | All 20 audit/report/cleanup fault combinations, real SQLite readonly/FULL and recovery tests, crash/nonce tests, plus a blocked final shutdown transaction that does not extend the caller's join budget. | PASS |
| 4 | Real CLI and desktop launcher/worker inherited-flag tests; ordinary non-pytest TestClient flags remain unable to activate analytics; explicit disposable runtime injection still works. | PASS |
| 5 | Read-only production source/service metadata test passed: baseline HEAD/source/version, no analytics package or process/unit activation flags, proposed analytics directory absent. No production database accessed or created. | PASS |
| 6 | Original source/resource/rule hashes and baseline differential passed; no NJIT rule, threshold, finding or report implementation changed. | PASS |

PR #660 remains open/draft at `e92025305178f26d1a3bea01f67f18764582feef`, and its
checkout is clean. No remote writes occurred. Production remains unchanged and this
candidate remains default-off. The additional request/response privacy probe sent a
sentinel through query, headers and body plus a synthetic IP; it persisted exactly
one page count and neither sentinel nor IP appeared in SQLite contents or files.
Database/directory permissions remained 0600/0700. Existing forbidden-field tests
and the six-table allowlist passed.

The collection measurements use five isolated subprocess trials per scenario,
1,000 accepted synthetic events, and bounded manual writer ticks. Each trial records
all timings, transaction counts, traced allocation and RSS. Contended mode forces
one real queue overflow while the loss lock is held; saturation forces 1,001 overflows;
recovery adds a successful heartbeat commit followed by a synthetic storage error and
reconnection. All modes persist exactly 1,000 events. SQL tracing and tracemalloc are
active, so these are instrumented processing measurements, not a latency guarantee.

| Mode (five trials each) | Producer p95 median ms | Writer transactions | Ten idle ticks median ms | Idle transactions | Peak traced bytes (max) | Added RSS MiB (max) |
|---|---:|---:|---:|---:|---:|---:|
| healthy | 0.022097 | 10 | 0.092236 | 0 | 200,029 | 0.430 |
| contended | 0.021960 | 11 | 0.094949 | 0 | 215,920 | 0.609 |
| recovery | 0.022003 | 13 | 0.087661 | 0 | 241,940 | 0.777 |
| saturated | 0.021932 | 11 | 0.092129 | 0 | 228,318 | 0.648 |

Healthy draining of 1,000 events took median **37.079 ms** (35.094–37.628 ms,
standard deviation 0.974 ms). Contended draining took **45.408 ms**
(44.987–48.373 ms, SD 1.386 ms); saturated draining took **46.351 ms**
(44.629–47.736 ms, SD 1.146 ms). The forced single-overflow timing including thread
creation was median 0.478 ms (0.303–0.592 ms). Recovery/reopen including the first
batch took median **12.332 ms** (11.823–12.714 ms, SD 0.385 ms), followed by a median
31.610 ms to drain the remainder. Its 13 transactions include both heartbeat attempts,
startup expiry and ten event batches. These phases are reported separately rather
than comparing a partial drain directly with a full drain.

Across all scenarios, ten idle ticks took **0.087–0.098 ms** with **zero transactions**.
Advancing the injected clock by 60 seconds produced exactly **one heartbeat transaction**,
taking 1.103–1.698 ms, without changing the loss marker. No recurring write amplification
or marker inflation was observed. Process-level RSS includes SQLite/thread/allocator
costs; tracemalloc and RSS are not universal peak-memory guarantees.

The existing real-background-writer benchmark also passed all producer/memory bounds.
Five separate-process trial pairs each used five warmups and 60 measured one-page PDF
audits. Median paired-trial p95 change was **+2.080%**, range **+1.014% to +5.262%**,
with between-trial SD **1.618 percentage points**. Individual samples and per-trial
statistics are preserved in `performance.json`; consistently sub-1% overhead remains
**unproven**.

A second bounded experiment used generated 40-page PDFs with text, headings and page
numbers: three separate-process trial pairs, three warmups and twelve measured audits
per process. Enabled samples include page/upload observations and a terminal event;
disabled samples have no collector or writer. Trial order is reproducibly randomized.

| 40-page trial | Disabled median / p95 ms | Enabled median / p95 ms | Median delta ms | p95 delta ms | p95 delta % |
|---|---:|---:|---:|---:|---:|
| 1 | 342.817 / 367.517 | 352.032 / 359.851 | +9.215 | -7.665 | -2.086% |
| 2 | 340.058 / 358.090 | 351.436 / 368.181 | +11.378 | +10.091 | +2.818% |
| 3 | 345.681 / 363.308 | 346.925 / 379.782 | +1.244 | +16.474 | +4.534% |

The small sample supports only descriptive conclusions: median differences were
+1.244 to +11.378 ms and p95 differences −7.665 to +16.474 ms. Scheduling, filesystem,
process and writer effects can contribute to this spread; the experiment does not
isolate their individual causes. No fixed acceptable-overhead threshold, statistical
significance, loaded-service guarantee or consistent sub-1% claim is inferred. No
unrelated auditor optimization was attempted.

To repeat the additional measurements from this worktree, use:

```bash
PYTHONPATH=src:tests .venv/bin/python .runtime/stage-b-final-corrections/run_pipeline_benchmark.py
PYTHONPATH=src .venv/bin/python .runtime/stage-b-final-corrections/run_workloads.py
```

For the full test selection above, change the three output paths from
`stage-b-validation` to `stage-b-final-corrections`; retain the explicitly authorized
baseline and read-only production metadata variables. No benchmark accesses production.

**Integration readiness:** ready for independent review of these uncommitted targeted
corrections. Commit/PR creation, deployment and activation are not authorized by this
record. Operational/institutional activation prerequisites and the documented limits
of RAM delivery, process death, storage availability and performance qualification remain.
