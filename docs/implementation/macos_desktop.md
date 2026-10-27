# macOS private development candidate

This implements a native build path, **not native qualification or distribution
approval**. Development host: Linux x86_64, CPython 3.12. No macOS app or DMG was
built here. Apple Silicon and Intel are separate, unqualified targets. Do not
publish artifacts, enable downloads, merge, deploy, or distribute to students.

## Starting point and retained architecture

Verified base: `35be6735a3b7f165b0211e1aa3eb2702d072368d`, draft #636,
stacked on #635 at `8d7a014bfee1df640731fda22963b9f28389f3aa`. The ancestry
also includes #634/#627/#625; those PRs remain open. Their dependency history
must be preserved during review. The prior Linux campaign's local
`experiments/student-beta-soak-20261027T043130Z/final_report.md` records 20
trials, 596 passes, zero failures, and no remaining owned processes. That soak
campaign was not repeated. It does not establish macOS compatibility.

PyInstaller's existing one-folder spec now constructs a windowed `BUNDLE` on
Darwin. Python, imported detector modules, native PDF libraries, shared HTML,
rule data, fonts, and notices travel inside the app. Finder launches the
bundled executable; students need neither Python nor terminal/server setup.
The UI and detector algorithms remain shared with the web application.
No additional application framework was introduced. Tcl/Tk already supplied
the launcher's optional window and is now required in the Mac build.

The server reserves its listening socket on `127.0.0.1:0` before starting
Uvicorn and passes that same socket to the server. It opens the existing UI
in the default browser with a per-launch authentication ticket. Existing
Host/Origin/session/CSRF protections, two-worker limit, 120-second audit
deadline, cancellation, exports, PDF viewing/highlights, filters, navigation,
About, and official-checklist access remain. Desktop never registers the URL
import route, even if a web deployment enables that feature.

Application Support is `~/Library/Application Support/NJIT Thesis Auditor`.
The app root, `audits/`, and upload-spool `tmp/` are made user-private with
mode 0700. The bundle is read-only at runtime; no audit is stored inside it.
A lock prevents two copies from cleaning each other's data. Startup removes
abandoned temporary work; controlled Quit deletes local audit/spool files.
Browser-saved reports remain the user's files. Deletion is not secure erasure.
The startup lock and all storage must be checked on native APFS/macOS.

Browser **Quit**, launcher **Quit**, launcher-window close, Command-Q, and
the Tcl/Tk macOS Quit event use the existing supervised shutdown. SIGTERM
requests controlled shutdown on the Mac main thread. Finder/Dock reopen
reopens the browser. Closing the browser alone is not Quit. Idle/session
shutdown remains. macOS workers use POSIX process groups; after SIGKILL and
root-process wait, the supervisor checks that the group has disappeared,
allowing launchd to reap orphaned descendants. Failed termination retains
ownership and files for retry. Force Quit/power loss cannot promise immediate
cleanup; the next start clears abandoned work. No Linux subreaper API is
called on Darwin. Native process behavior remains unverified.

## Builder commands (developers only)

Build independently on an actual Apple Silicon Mac and an actual Intel Mac,
with matching native **CPython 3.12** including non-system Tcl/Tk, a graphical
login, and Apple's command-line tools (`lipo`, `otool`, `codesign`, `hdiutil`).
The tool rejects other OSes, architecture mismatches, Rosetta execution, dirty
worktrees, and reused output/build environments. It does not install Python
or Apple's tools, purchase credentials, or upload anything.

From a fresh committed checkout of this candidate:

```bash
python3.12 packaging/build_offline_macos.py --arch arm64 --dmg
# On a separate native Intel checkout/host:
python3.12 packaging/build_offline_macos.py --arch x86_64 --dmg
```

`--dmg` is optional. Each command creates a dedicated virtual environment,
installs the existing pinned constraints plus the project and PyInstaller,
checks Tcl/Tk and native PDF imports, freezes the existing spec, verifies
bundle structure/resources/architectures/signature integrity, and saves the
installed dependency freeze. If runtime notices are absent from standard
locations, supply **matching installed-version** license files through
`NJIT_MACOS_TCL_LICENSE` and `NJIT_MACOS_TK_LICENSE`; missing notices stop the
build. Do not substitute an unrelated runtime's license. The dependency
snapshot is version-pinned; it is not a byte-identical, hash-locked build.
Retain the exact Python installer, tool versions and wheel hashes for a
release reproducibility review.

Expected outputs, **not created on Linux**:

- `dist/macos-arm64/NJIT Thesis Auditor.app`
- `dist/macos-x86_64/NJIT Thesis Auditor.app`
- Optional `dist/macos-<arch>/NJIT-Thesis-Auditor-macos-<arch>-private.dmg`
- `bundle-inspection.json` and `build-dependencies.txt` beside each app.

The inspector checks every Mach-O file's available architectures, bundles'
internal symlinks, required data/runtime/notices, and `codesign --verify
--deep --strict`. It records load commands for dependency/minimum-OS review.
Signature integrity is **not Developer ID verification or notarization**.
The builder contains no publish, upload, notary submission, or CI dispatch.
The existing Windows release configuration and production stay unchanged.

## Architecture and operating-system limits

The pinned [PyMuPDF 1.28.2 release metadata](https://pypi.org/pypi/PyMuPDF/1.28.2/json)
provides `macosx_11_0_arm64` and `macosx_10_15_x86_64` stable-ABI wheels.
These establish wheel availability, **not this app's minimum OS**. Other
native libraries and Tcl/Tk impose their own requirements. There is no
universal2 or Rosetta support claim. PyInstaller verifies architecture
compatibility and signs collected native binaries; see its
[macOS guidance](https://pyinstaller.org/en/stable/feature-notes.html).

`LSMinimumSystemVersion` conservatively equals the full build-host macOS
version. Build on each intended baseline, inspect native load commands,
and test there and on newer intended releases. Merely lowering the plist
value cannot establish compatibility. No macOS release is qualified yet.
Choose the test matrix from Apple's current
[security releases](https://support.apple.com/en-us/100100) and
[Mac hardware compatibility](https://support.apple.com/macos); support is a
record of actual hardware/OS/browser tests, not an assumption from wheel tags.
Safari's embedded PDF support must be checked directly; Linux Chromium and
Firefox results do not establish Safari PDF/highlight behavior.

## Install, use, uninstall (private local testing only)

For a locally built, permitted private-test app: open the optional DMG in
Finder, copy **NJIT Thesis Auditor.app** to **Applications** (or the user's
Applications folder), eject the DMG, and open the copied app through Finder.
Without a DMG, copy the whole `.app` bundle. Keep Gatekeeper enabled. An
unsigned/ad-hoc, unnotarized candidate can be blocked; stop and record that
result. This guide provides no quarantine-removal or security-bypass steps.
A blocked launch is not a successful installation test.

Select a synthetic PDF in the browser. Use **Quit** in the browser or launcher
when finished. Command-Q/window close also request cleanup. The native
launcher remains visible for opening the browser again and quitting.

To uninstall, Quit first, move the app to Trash in Finder, and remove
`~/Library/Application Support/NJIT Thesis Auditor` using Finder's **Go to
Folder** if residual local data exists. Remove a retained DMG separately.
Downloaded reports outside Application Support are not automatically removed.
Do not delete Application Support while an audit/app instance is running.

## Native validation

Builder/tester Python commands below are never student installation steps.
Use a separate validation venv; no private PDFs are needed:

```bash
python3.12 -m venv .venv-validation
.venv-validation/bin/python -m pip install -c packaging/offline-build-constraints.txt -e '.[dev]'
.venv-validation/bin/python scripts/validate_macos_desktop.py \
  --bundle 'dist/macos-arm64/NJIT Thesis Auditor.app' \
  --output /tmp/njit-macos-native-smoke.json
.venv-validation/bin/python -m pytest -q \
  tests/test_macos_desktop.py tests/test_pdf_url_disabled.py \
  tests/test_offline_desktop.py tests/test_desktop_executor.py
```

Substitute `macos-x86_64` on Intel. The native script checks actual frozen
startup with no Python on PATH, browser-open invocation using an isolated
capture helper, local service/authentication, corrupt upload, five successful
audits across two launches using the same isolated HOME, four-format export
parity, PDF/highlight parity, About/rules, disabled URL requests, Quit, closed
listener, and temporary cleanup. It compares normal/Unicode/rotated/low-text
synthetic inputs to same-checkout web outputs; only IDs, paths and recorded
audit timestamps are normalized. It does not open the real default browser,
exercise Finder/Tk, prove OS-level egress isolation, or qualify installation.
It must run with the pinned dependencies and matching source commit. Logs
and launch tickets stay in its temporary private directory and are deleted.
On failure it returns nonzero; never label partial smoke output a pass.

Run the browser cases after installing the test browsers on the Mac:

```bash
.venv-validation/bin/python -m playwright install chromium firefox
NJIT_REQUIRE_BROWSER=1 .venv-validation/bin/python -m pytest -q \
  tests/test_offline_desktop_browser.py tests/test_student_ux_browser.py \
  tests/test_student_results_browser.py
```

Then perform and record this manual matrix for **each architecture and OS**:

| Check | Native acceptance evidence |
| --- | --- |
| Install/Finder launch | Clean session without Python; copied app and optional DMG; Gatekeeper result |
| Local initialization/browser | Real default Safari, then Chrome/Firefox where available; reopen Dock/Finder |
| Upload/detectors/results | Synthetic PDF, findings, filtering/navigation, About and official checklist |
| PDF/highlight viewer | Inline PDF, correct pages/boxes and navigation in each browser |
| Downloads | PDF, text, Markdown, JSON save/open and source parity |
| Bad/repeated inputs | Corrupt/encrypted PDF recovery and consecutive successful audits |
| Concurrency/deadline | Two running workers; queued acceptance deadline, timeout, cancel, retry |
| Shutdown | Browser/launcher Quit, Command-Q, menu Quit, window close, SIGTERM |
| Process cleanup/restart | No owned listener/descendants; same-root restart and a later successful audit |
| File permissions | APFS, spaces/Unicode names, read-only bundle, locked directories, symlink rejection |
| Security | Foreign Host/Origin/CSRF and unauthed rejection; URL audit unavailable |
| Network isolation | Internet disconnected with loopback available; uploads, detectors, viewer/exports work |
| OS isolation evidence | Inspect listener addresses and owned-process egress, distinguishing browser traffic |

The existing executor tests provide real short-lived hung workers, descendants,
queued deadlines, termination failures and cancellation/recovery; run them
natively as well. Capture build SHA, app hash, exact OS/hardware/browser,
notices and every result. Do not reuse Linux simulations as native passes.

## Signing, licensing and release gates

PyInstaller applies ad-hoc signatures for local Mac builds by default;
that is necessary native-code integrity handling, not a trusted publisher.
Ordinary student distribution needs an approved signing identity, a
Developer ID Application certificate, hardened runtime, notarization and
Gatekeeper/quarantine testing of the final delivered bytes. Apple's
[notarization workflow](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
and [Developer ID certificate guidance](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/)
describe the Apple Developer Program credentials required. No credentials
were assumed available, discovered in keychains, used, purchased or requested.
No notary upload is authorized here. Notarization does not clear licensing.

See [licensing and checking-rule disclosure](macos_license_review.md) for the
new Mach-O tooling/runtime notices and the source-disclosure questions.
Native install/runtime qualification, current-OS matrix, Safari viewer,
OS-disconnected testing, signing/notarization and formal licensing/distribution
approval all remain release blockers. Windows native qualification also
remains open; this task does not change its status.

## Linux development validation for this change

CPython 3.12.3/Linux x86_64: 4,874 safe non-browser tests passed, 46 documented
private/historical or fixture-dependent cases deselected; 23 real browser
cases passed (Chromium/Firefox coverage inherited from the existing browser
suite, including two new default-disabled UI cases). Final scoped web/template
regression: 278 passed, three fixture-dependent cases deselected. These overlap
the safe suite and are not additional unique passes. Ruff and mypy pass (158
source files). Eight portable Mac policy tests are simulations, not native
results. Four synthetic PDF classes preserve desktop/web machine findings,
text/Markdown/JSON exports and PDF report/highlight content and drawings.
No detector/rule-data/release-gate/deployment configuration changes exist.

The initial safe-suite attempt found 20 obsolete enabled-URL expectations;
the affected tests now explicitly configure reactivation or assert the disabled
default, and the final run passes. Initial new desktop-route tests expected
404, while the existing router returns 405 for an unregistered POST matching a
GET job path; the tests now accept either rejection. The native smoke script
uses the same expectation. No feature was enabled merely to make defaults pass.
The prior 596-outcome soak and native-Windows limitations remain historical
evidence; they were not rerun or converted into Mac qualification.
