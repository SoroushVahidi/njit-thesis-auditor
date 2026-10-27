# Desktop audit deadline, cancellation, and native release gate

The desktop uses two supervised audit processes, rather than running PDF work
inside the local HTTP server's Python threads. Each accepted audit has a
120-second wall-clock deadline, including framework/worker queueing, startup,
detector execution, and initial JSON/Markdown/text report creation. The desktop
server only supervises those processes and renders the existing interface.
The hosted web executor and detector thresholds are unchanged.

**Cancel audit** stops the selected worker; the failed-state message says the
audit was cancelled. **Quit**, closing the launcher window, idle shutdown, and
session expiry all close the same executor before requesting server shutdown.
Expired work says: “This audit took too long and was stopped. Try a smaller PDF
or audit it again.” Normal completed audits use the existing report pipeline.

On Linux, each worker has its own process group. On Windows, it is assigned to
an unnamed Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. The worker
waits for a supervisor handshake before importing or running document code.
Failure to establish containment fails the audit; it never retries without
containment. The supervisor kills remaining descendants, reaps the worker,
and only then removes request/result files and timed-out/cancelled workspaces.
Worker stdout/stderr are discarded so native parser exceptions cannot become
document text, paths, or bearer IDs in application logs. Worker Python socket
and DNS operations are denied. An OS-level network-off test is still required.

Process-tree reaping has a two-second wait per worker. The local server has a
five-second graceful-shutdown allowance, and launcher joins are bounded to ten
seconds plus a two-second forced-server-exit attempt. These are cleanup limits,
not permission to leave a stuck audit running. They do not interrupt arbitrary
Python threads: document auditing is in the killable processes. OS termination
or filesystem failures must be surfaced rather than treated as deletion success.
Failed file cleanup remains visible and can be retried with Delete all; ordinary
deletion is not secure erasure. Lazy interactive PDF/highlight rendering retains
its existing shared route implementation; this change bounds the audit pipeline.

Worker state travels as JSON with explicit representations for tuples, integer
keys, page rotation, and highlight styles. No pickle or executable state is
accepted. This preserves exact finding IDs, severity, measurements, locations,
and report/highlight presentation across the process boundary. Protocol files
live only in the application's private audit workspace and are removed after
processing. Original PDFs and initial reports for completed jobs retain the
existing delete/Quit behavior.

## Native Windows availability checked on October 26

PR #635 was verified at `57b1533f3168ead6bfc1b7144598eb2aea98546e`.
The local host is Linux x86_64. No configured Windows SSH alias, VM manager,
Windows VM process, or connected Windows execution tool was found. `/dev/kvm`
alone is not an installed or authorized Windows guest. No OS was installed,
license agreement accepted, paid service activated, or billing changed.

The repository's self-hosted runner API returned zero runners; its configured
CI uses `ubuntu-latest`. The latest available Actions run,
[39086583330](https://github.com/SoroushVahidi/njit-thesis-auditor/actions/runs/39086583330),
failed before runner assignment. Its check annotation cites “recent account
payments have failed or your spending limit needs to be increased”. Actions are enabled at repository level, but that does
not establish a working Windows runner or resolution of the account restriction.
No new job was dispatched to test or bypass that restriction.

**Smallest unblock:** provide access to an existing, authorized Windows 10 or
11 x64 machine (including an already licensed VM), or an authorized working
Windows runner. A builder needs Python 3.12 x64; a separate clean no-Python
Windows session/machine must exercise the extracted ZIP. Test both Windows
versions only when available. Do not infer a Windows pass from Linux, mock PE,
or pure version-resource serialization checks.

## Native checks still required

Run the existing native build script and smoke checklist. In addition, run
`tests/test_desktop_executor.py` and the desktop browser lifecycle case on the
Windows build/test host: success, accepted/queued timeout, cancellation, Quit
with running and queued work, process-tree termination, cleanup, and a later
successful audit. The browser case also quits and reopens the same local data
root. Verify real Job Object behavior and absence of live orphan workers.

On a clean Windows machine, extract the actual ZIP in a user-writable directory,
launch without Python or terminal steps, and test the default browser, native
window close, icons/version, reports/highlights, ACLs/junctions, and Defender/
SmartScreen. Disconnect internet access while preserving loopback and repeat
PDF auditing and exports. Do not disable protections or bypass a warning.
Signing/publisher policy remains a release decision; signing is not a promise
that a new package will receive no reputation warning.

The public website remains `enabled=false`, `preview=false`. No Windows ZIP,
Windows checksum, Windows offline verification, public release, merge, or
production deployment is claimed by this preparation work.
