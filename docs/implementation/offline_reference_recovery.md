# Offline Help and Rule Reference investigation

The verified starting revision is draft PR #636,
`35be6735a3b7f165b0211e1aa3eb2702d072368d`. On October 27, 2026, GitHub
and the remote branch heads confirmed the open draft stack:

| PR | Head | Base |
| --- | --- | --- |
| #634 | `efed063b2cb9a97ddecfc050afe16846a84df8eb` | #627 |
| #635 | `8d7a014bfee1df640731fda22963b9f28389f3aa` | #634 |
| #636 | `35be6735a3b7f165b0211e1aa3eb2702d072368d` | #635 |

Git ancestry checks confirm both parent relationships. The newer draft #637
at `79a37fcc16a08e7db4b3f04d8f759a9bbe6c5e19` is a sibling on #636. Its
macOS builder, bundle inspector, launcher changes, and shared resource list
were inspected; it does not repair reference-page recovery. This work stacks
separately on #636, without importing URL deactivation or macOS lifecycle work.
Existing worktrees, including dirty ones, and stashes were left untouched.

## Findings and limits of reproduction

The reported inability to open both pages **was not reproduced on this
baseline**. Authenticated source requests return HTTP 200 for `/help` and
`/rules`. A real Linux PyInstaller build from the baseline also navigates to
both pages from home and audit results, filters the catalog, and follows rule
anchors while browser requests outside the loopback origin are blocked.

Both routes are copied into the desktop route table from the shared web app.
Links use root-relative local paths; no external script, stylesheet, font,
fetch, or website is needed to render these pages. CSS and JavaScript are
inline. `packaging/offline_desktop.spec` already bundles their templates,
`base.html`, and `project_added_rules.json`. `resource_paths.py` resolves those
files from the checkout in source mode and `sys._MEIPASS` when frozen,
independently of the current working directory. Neither route exclusion nor
missing entries in the packaging spec was established as the reported cause.

Three narrower defects were reproduced:

1. The desktop template global `retention_notice` was a lambda, but Help and
   About render it as a value. Jinja displayed the function representation,
   including an internal name and address, instead of the local privacy notice.
2. The catalog loader swallowed missing/unreadable/invalid-JSON errors and the
   route rendered a successful empty catalog, saying “0 rules.” Some malformed
   JSON structures instead caused uncaught exceptions.
3. A missing Help, Rule Reference, or inherited base template caused an
   unhandled template exception and generic HTTP 500 rather than actionable
   recovery. This is fault-injection evidence, not evidence that a distributed
   package omitted those resources.

To identify the original page-opening failure, obtain the affected OS/version,
desktop build commit/version and package checksum, exact click path and local
URL, visible error/status, whether the full package was extracted, and whether
home/auditing still work. Do not collect PDFs, session tickets/cookies, CSRF
tokens, or unredacted paths. An older or incomplete package remains a possible
explanation, not a diagnosis.

## Correction

Store the existing local retention sentence as a string. Return HTTP 503 and a
clear recovery notice instead of an empty Rule Reference; the shared web
route advises retrying later, while desktop advises replacing the application
with a complete copy. Reject malformed catalog containers without altering
any valid catalog entries or wording.

The desktop catches missing-template errors with a small standalone HTML page,
so recovery does not depend on another bundled template. It offers Home and
the existing protected Quit action and includes no exception text, file path,
document content, or diagnostic identifiers. Authentication still runs before
page handling, and the response retains the existing CSP/cache headers.

Help and Rule Reference identify their content as locally available. Official
NJIT links on About and results are labeled “external; internet required” and
open separately in desktop mode, so an unreachable website leaves the local
app available. The approved limitation disclosure and NJIT rule wording remain
unchanged. Shared web links retain their existing behavior.

## Regression coverage and qualification

`tests/test_offline_reference.py` covers blocked socket/DNS operations,
navigation, session/Host/Origin/cross-site/CSRF protections, missing templates,
catalog permission/encoding/JSON/container errors, recovery, shared web
behavior, and the real spec's data declarations copied into a simulated frozen
resource root without source-directory fallback. Against the baseline, 22
cases fail and 2 pass; the corrected targeted suite passes 164 tests.

`tests/test_offline_reference_browser.py` checks Chromium and Firefox at
320/390/768/1440 pixels: home/results navigation, rule anchors, search/reset,
overflow, blocked external references, continued local use, and protected Quit.
Set `NJIT_REQUIRE_BROWSER=1` to require browser binaries. Set
`NJIT_REFERENCE_EXECUTABLE` to an actual Linux PyInstaller launcher to add
frozen cases with an unrelated working directory and Python absent from PATH.
The optional fixture is explicitly Linux-only; it is not a Windows or macOS
qualification harness. Browser interception alone is not an OS network-isolation
test. Exact final counts, commands, JUnit results, build logs, and synthetic
evidence are retained outside Git under `notes/offline_help_rules_20261027/`.

Existing desktop tests cover invalid/encrypted PDFs, repeated audits,
worker crashes, timeout/cancellation, cleanup retry, process containment,
Quit, startup link/junction guards, report-path protection, and simulated
Windows Job Object failures. Those mechanisms were inspected and retained.
Closing a browser tab leaves the existing launcher/server alive for reopening;
Quit, launcher close, idle expiry, and session expiry retain their existing
shutdown paths. No lifecycle rewrite is included.

Linux is the available native execution/build environment. Windows packaging
and the sibling macOS packaging configuration were inspected; shared resource
and mocked tests do not establish native compatibility. Native Windows and
macOS execution remain unverified in this task. Existing OS, licensing,
signing, clean-machine, and release-approval gates remain in force. No installer
publication, public-distribution readiness, OS-disconnected qualification,
feedback submission, telemetry, or automatic update feature is claimed.

No detector, threshold, canonical rule, severity/confidence calculation,
finding/location/measurement, highlight geometry, report schema, anonymizer,
download configuration, production service, or existing PR is changed. All
document processing in validation uses synthetic PDFs.
