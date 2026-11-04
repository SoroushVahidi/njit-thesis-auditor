# Offline desktop Windows release readiness — 2026-10-16

**Decision: NO-GO for Windows distribution.** This audit ran on Linux x86_64. A genuine Windows x64 host was unavailable, so the candidate has no native Windows build or packaged Windows launch, storage, browser, or shutdown result. No application was distributed or deployed.

## Scope and revision

- Starting branch: `audit/offline-desktop-autonomous-20261016T044750Z` at `ae0d00be4f5dfd5ac574912a001dffced69a9181` (PR #620 was open at this SHA; its branch was not changed).
- Expected base verified: `origin/main` at `4efd780dde53eea907a714df8bfed86e923ef86a`. A different local `main` ref was left untouched.
- Ending audited implementation SHA: `02e157660f66152070fd5a73521565cff9fa476c` on the isolated audit branch. The final documentation commit is recorded in the private `FINAL_REPORT.md`.
- All new inputs were synthetic. Detailed logs and synthetic artifacts are in the private run directory `.offline-release-runs/20261016T044750Z`, outside this worktree.

## Verified issues and changes

| Issue | Evidence | Narrow fix |
| --- | --- | --- |
| Startup cleanup followed a linked `audits/` or `tmp/` directory and could delete files outside the app root. | Synthetic sentinel directory, linked as either storage directory; startup previously traversed it. | Refuse linked or Windows reparse-point storage roots before cleanup, including with Python 3.10/3.11. Remove child junction entries with `rmdir` without traversing their targets. Guard the launcher lock and final temp cleanup. Regression tests preserve an outside sentinel; native Windows junction behavior still needs a smoke test. |
| JSON, Markdown, and text report downloads followed a symlinked report file outside the runtime directory. | A synthetic completed job returned HTTP 200 and the outside sentinel through `/download/json` before the fix. | Require each report path to resolve inside the runtime directory, treating symlink loops as unavailable. Regression tests cover all three routes and a loop; they now receive 404. |
| Combined report and highlight failures could put job IDs and exception tracebacks, including paths or document-derived messages, into logs. | Code review of `_logger.exception` and `exc_info=True` call sites; a forced synthetic exception proved the combined report leak path. | Log only exception class for these failures and omit job IDs from highlight warnings. Regression tests check forced combined-report and highlight failure logs and responses. |

These guards reduce accidental exposure and cleanup risk. They do not establish secure disk erasure or comprehensive confidentiality against a process already running as the same user, filesystem races, browser extensions, OS telemetry, or saved browser downloads.

## Validation record

| Exact command or check | Result | Evidence and limit |
| --- | --- | --- |
| `python -m pip install -e '.[dev]'` | PASS | Editable install completed; `pip-install.log`. |
| `ruff check .` | PASS | All checks passed after the final code edits. |
| `mypy src` | PASS | No issues in 149 source files after the final code edits. |
| `python -m pytest -q tests/test_offline_desktop.py` | PASS | 25 tests: auth, Host/Origin/CSRF, delete/retry, symlinks, log redaction, online/offline parity, malformed and encrypted PDFs, and no socket connect/DNS in the tested audit paths. |
| `python -m pytest -q tests/test_web_app.py` | PASS | 218 web route tests on the final source, including the shared report and PDF routes; `pytest-web.log`. |
| `python -m pytest -q tests/test_offline_desktop.py tests/test_web_app.py` | PASS | 243 combined tests on the final code commit, 8.84 seconds; `pytest-offline-web-final.log`. |
| `python -m pytest -q` | PASS | 4,780 passed, 6 skipped, 3 warnings in 197.15 seconds; `pytest-full.log`. This run began before the final small report-link, log, and test edits. The final 25-test offline suite, Ruff, and mypy were rerun afterwards. |
| `git diff --check` | PASS | No whitespace errors. |
| Existing Linux one-folder executable (SHA-256 `849b7e5cd5910cf18aa1a86150df73b4837c590c6f284be2f4ffbe5195cc1a05`) | PASS for prior candidate only | Built from `7f6b165`, before this audit's fixes. Actual executable on Linux bound `127.0.0.1` only; unauthenticated index/report and wrong Host returned 403. Ticket launch, synthetic upload, status, JSON/Markdown/text/combined PDF, original/highlighted PDF, job/sort pages, delete and Quit returned expected statuses. Listener and temp work cleared. `packaged-smoke-results.log`. This is not a packaged pass for the ending SHA. |
| Intermediate source package from broad development environment | FAIL as release bundle | PyInstaller produced 7,987 files / 5.4 GB and included unrelated cloud and credential-library modules from the builder environment. The executable SHA-256 is `d50cc21185603c07661c134a728265f3c5fe42d68e139f8a9b4f92be1cde1de3`. Synthetic packaged upload, reports, symlink denial, delete, Quit, and loopback-only syscall trace passed, but this bundle must not be distributed. No private sample names were found in a filename/TOC search; that is not a byte-level confidentiality proof. `final-packaged-smoke-results.log`, `final-network-trace.log`, `final-bundle-toc.txt`. |
| Clean pinned Linux one-folder package from `02e1576` | PASS on Linux only | Built with `clean-build.sh`: new isolated Python 3.12 venv, `pip install -c packaging/offline-build-constraints.txt -e . pyinstaller`, then `python -m PyInstaller --noconfirm --clean --distpath ... --workpath ... packaging/offline_desktop.spec`. Exit 0; 49 installed packages, 118 bundled files, 132 MB; launcher SHA-256 `e676dfb553f6d7c3dbbeebd482e779b07e36b53479dca8677b62c2375f7f51ae`. Actual packaged smoke passed ticket login, synthetic upload, all listed reports and PDFs, sorting page, linked report denial, two concurrent uploads with distinct complete jobs, deletion, Quit, abandoned workspace/temp cleanup, and 0700 app/audit/tmp directories. A second instance exited without disrupting the first; a linked `tmp` root was refused and its outside sentinel survived. `clean-packaged-smoke-results.log` and `clean-link-test.log`. |
| Clean Linux bundle privacy inspection | PASS with limited scope | Recursive PyInstaller archive table of contents and bundled filenames had no private sample, review-ledger, raw-data, `.env`, cloud SDK, URL-fetch, or web-sample names. The clean venv freeze also had no unrelated cloud SDKs. This is a name/TOC inspection, not a byte-level confidentiality proof. `clean-bundle-toc.txt`, `clean-build-freeze.txt`. |
| Native Windows x64 build and smoke | NOT TESTED | Host is Linux x86_64; no genuine Windows environment was available. `packaging/build_offline_windows.ps1` and `docs/implementation/offline_desktop_windows_smoke.md` provide the reproducible build and required checks. |
| Independent review of this branch's fixes | PASS with platform limit | Three `codex review --uncommitted` passes found a child-junction removal bug, a Python 3.10/3.11 junction detection gap, and a symlink-loop 500. All were fixed; the final pass found no actionable defects. Native Windows behavior remains unverified. Logs: `independent-review*.log`. |

## Parity and adversarial coverage

The clean build used these exact commands from the worktree root, with `RUN` set as shown. The build script, full output, freeze, and hashes are preserved in that run directory.

```bash
RUN=/home/soroush/njit-thesis-auditor/.offline-release-runs/20261016T044750Z
python -m venv "$RUN/clean-venv"
"$RUN/clean-venv/bin/python" -m pip install -c packaging/offline-build-constraints.txt -e . pyinstaller
"$RUN/clean-venv/bin/python" -m pip freeze > "$RUN/clean-build-freeze.txt"
"$RUN/clean-venv/bin/python" -m PyInstaller --noconfirm --clean --distpath "$RUN/clean-dist" --workpath "$RUN/clean-build-work" packaging/offline_desktop.spec
```

The clean packaged process was traced with `strace -f -e trace=socket,bind,connect,listen` during the synthetic smoke. It bound only `127.0.0.1`, recorded no `connect()` syscall, and left no listener or audit/tmp entries after Quit. This is process-level evidence for that Linux run, not a disabled-network namespace or native Windows packet capture.

The in-process parity suite compares normal, Unicode, rotated, and low-text synthetic PDFs across online and offline routes for normalized JSON, Markdown, text, combined PDF content/drawings, original and highlighted pages, finding order, filter script, cards, sorting, and status counts. A new encrypted synthetic PDF had the same failed job state and error message on both apps. Malformed PDF handling was compared in both apps; a malformed PDF and a PDF containing an external URI link caused no socket connect or DNS lookup in the instrumented test. Odd upload names stayed in the generated job workspace. These are application-level checks; no disabled-network namespace or native Windows packet capture was available in this audit.

The offline session gate requires a launch ticket, a cookie, exact loopback Host, same Origin for mutations, and a CSRF token. The existing tests cover unauthorized report/PDF access and deletion. The clean Linux packaged smoke confirmed unauthorized requests were rejected. The single-instance lock rejected a second packaged launch against the same test data root; Quit removed the listener and temporary audit work. Two concurrent synthetic uploads completed with distinct job IDs and were deleted. Eight-hour expiration, 30-minute idle shutdown, a real browser filter interaction pass, and Windows ACL behavior remain untested on a native Windows package.

## Release blockers and next gate

1. Build the ending SHA on native Windows x64 with the PowerShell script; inspect the complete one-folder bundle, not only its launcher hash.
2. Complete every native packaged smoke step, including real browser filters/navigation, packet capture or firewall evidence, concurrent uploads, ACLs, deletion, and clean shutdown.
3. Review the native Windows smoke evidence and address any platform-specific findings before distribution.

The recommendation is to keep Windows distribution blocked until these gates pass. The Linux development evidence supports continued testing only; it is not a Windows release authorization. The broad-environment bundle is separately blocked by unrelated packaged dependencies; the isolated pinned build avoided those dependencies.
