# Offline desktop release readiness — 2026-10-16

**Recommendation: NO-GO for Ester.** The portable source and native Linux development package passed the local checks below. No native Windows x64 builder or clean Windows user environment was available, so the mandatory Windows build, browser, profile, deletion, network, and shutdown gates remain **NOT TESTED**. Do not distribute this candidate or describe it as a verified Windows application.

## Provenance and scope

- Starting point: open PR [#620](https://github.com/SoroushVahidi/njit-thesis-auditor/pull/620), head `ae0d00be4f5dfd5ac574912a001dffced69a9181`; verified `origin/main` at `4efd780dde53eea907a714df8bfed86e923ef86a` before work.
- Isolated branch: `verify/offline-desktop-windows-readiness-20261016` in `worktrees/offline-desktop-release-readiness-20261016`. The original PR, main, and production worktrees were not edited.
- Hardening commits: `705eaf25c98487fa90c9bded10b9e42959baf957`, `4ef0ff9f51c7f096f6b34fce4b14052a9f8934de`, and final source `10a7cba272e044587384f45ef2fa1d827341ba74` (all `[skip ci]`). No detector thresholds, rule identities, or report rendering logic were changed.
- Evidence: local dated directory `/home/soroush/njit-thesis-auditor/notes/offline_desktop_release_readiness_20261016/`, outside the tracked worktree. All PDF inputs were generated synthetically. GitHub Actions was not run because of the known billing restriction. Local results are not CI results.
- Independent read-only review: **APPROVE** for the updated portable source, privacy controls, packaging workflow, Origin/Referer adjustment, route exclusion, and linked-lock fix. The reviewer first returned **REQUEST_CHANGES** for the hard-link case; that finding was fixed and re-reviewed. `review_verdict.md` in the dated evidence directory records the verdict sequence. Native Windows behavior was explicitly outside the final approval.

## Verified defects and changes

| Finding | Resolution and regression evidence |
| --- | --- |
| Authenticated multipart and small form bodies could be buffered without a pre-parser bound. | Bounded Content-Length and streamed body size before parsing; oversized requests return 413. `tests/test_offline_desktop.py` covers both paths. |
| The launch ticket could be reused, and the launcher window could offer a stale ticket. | Ticket is single-use, expires after two minutes, and **Open auditor** issues a fresh one. Replay and expiry tests pass. |
| PDF library errors could put an absolute local upload path in a browser error page; shared web logs could include a job token or traceback. | Offline failures use a generic page; offline mode suppresses shared web-app log records and emits only count-based cleanup warnings. Tests assert absence of path, token, and exception detail. |
| Symlinked managed directories, including Windows NTFS junctions, could redirect cleanup outside the app root. | Startup, runtime requests, deletion, and final cleanup reject linked managed boundaries; entry deletion unlinks a link or junction itself. Synthetic sentinel targets survive regression tests. Native Windows junction behavior still needs testing. |
| Delete all could leave multipart spool files; Quit could silently fail cleanup. | Spool cleanup is queued while work is active and drained afterward. Browser and Tk Quit report cleanup failure for retry. Active-audit and failed-deletion tests pass. |
| Browser form submission could carry `Origin: null` under a strict no-referrer policy. | Normal offline pages now use `Referrer-Policy: same-origin`; the launch-ticket redirect retains `no-referrer`. A narrow null-Origin case also requires same-origin fetch metadata, exact loopback Referer, the session cookie, and CSRF. Focused review **APPROVE**; real Firefox sent the expected loopback Origin and Referer in the corrected run. |
| The offline app copied the online `/openapi.json` route even though its own OpenAPI setting was disabled. | The offline route filter now excludes that copied route; a test asserts it is absent and returns 404 after authentication. |
| A linked `desktop.lock` could make launcher startup write one byte to a file outside managed storage. | The launcher rejects symbolic links and junctions, uses `O_NOFOLLOW` where available, and rejects opened files with more than one hard link before writing. Synthetic external sentinels remain unchanged in both regressions. Independent review requested the hard-link check, then returned **APPROVE**. Native Windows race/reparse behavior remains an acceptance gate. |

## Evidence from the frozen source commit

**Release-blocker matrix legend:** PASS means the named local gate was exercised successfully; FAIL means a verified defect remains; NOT TESTED means the required environment or test was unavailable. Current verified open FAIL gates: **0**. Mandatory Windows gates are **NOT TESTED**, which makes the overall release decision NO-GO.

| Gate | Result | Evidence / limits |
| --- | --- | --- |
| Ruff and mypy | **PASS** | `./scripts/validate_offline_linux.sh`, exit 0; Ruff passed and mypy found no issues in 149 source files. `exact_linux_build.log` / `.exit`. |
| Focused offline, web, highlight, and report tests | **PASS** | 267 passed, one library deprecation warning; exact source installed by the validation script, exit 0. `exact_linux_build.log`. |
| Full local pytest suite | **PASS** | 4,785 passed, 10 skipped, 3 warnings; branch source explicitly on `PYTHONPATH` in the frozen build venv; exit 0. `final_full_pytest.log` / `.exit`. The first ad hoc full run used an older editable checkout and is diagnostic only. |
| Same-source online/offline parity | **PASS** | Parameterized normal, actual Unicode, rotated-page, and low-text synthetic PDFs compare normalized findings, identities, severities, pages, measurements, locations, explanations, coordinates, reports, and highlighted/original pages. Malformed and encrypted synthetic PDFs exercise failure-page parity. `tests/test_offline_desktop.py`; no detector edits. |
| Linux x64 one-folder package | **PASS** | PyInstaller build, whole-folder inspection, and packaged synthetic HTTP smoke, exit 0. 194 files / 137 MB; launcher SHA-256 `80a70b37b7607406ac83499835186791b0f2c1be43cba70928e3daed6277435b`; SHA-256 of the sorted full-folder manifest `b42f6f3e6609980d46cdddb8a021af9e8f007dd87fb8e368a4fa35ee627e92f9`. `release_linux_bundle_sha256.tsv`, `exact_linux_build.log`. This is a Linux build, not a Windows executable. |
| Packaged browser interaction | **PASS** | Firefox headless against the actual Linux executable: upload, finding filter/reset, sort, original/highlight links, Delete this audit, Quit, empty managed audit/tmp dirs; exit 0. `packaged_browser_smoke.py`, `release_packaged_browser_smoke.log` / `.exit`. |
| Local session, route, and file access | **PASS** | Unauthorized page/PDF/report/highlight routes return 403; Host, Origin, CSRF, ticket replay, session expiry, and large-body tests pass. Packaged HTTP smoke checks protected routes and no listener after Quit. |
| Local storage lifecycle | **PASS on Linux** | Tests cover startup recovery, symlink targets, active deletion, second-instance lock, failed cleanup, and session expiry. Packaged smoke and browser run confirm Quit clears managed temp/audit files. Files saved by the user outside the managed directory are not deleted. Deletion is ordinary removal, not secure erasure. |
| Package privacy allowlist | **PASS with inspection limits** | Eleven project resources exactly match `packaging/offline_desktop.spec`; whole-folder name scan found no dissertations, private samples, ledgers, private notes, or likely credentials. Synthetic inspector regression test passes. Heuristic inspection is not a confidentiality certification. |
| Application-controlled network behavior | **PASS for traced Linux run** | `release_linux_trace.*` contains one AF_INET bind to `127.0.0.1` and one private AF_UNIX wrapper connect; no app AF_INET/AF_INET6 connect, sendto, or sendmsg to a remote host. `release_linux_smoke.log`, exit 0. Browser/extension/OS traffic was not attributed to the application. |
| Network physically disabled | **NOT TESTED** | This workstation disallows `unshare -Urn` and `bwrap --unshare-net` (both exit 1, operation not permitted). In-process tests deny outbound socket connects, and traced packaged behavior is local, but neither substitutes for an unplugged-network acceptance run. |
| Native Windows x64 package and acceptance | **NOT TESTED** | No Windows x64 host/VM or PowerShell was available. `scripts/build_offline_windows.ps1` and `docs/implementation/offline_windows_acceptance.md` provide the build, unauthenticated socket smoke, and complete manual gates. Script execution, Windows ACL/junction behavior, Tk/default browser, clean no-Python profile, antivirus/SmartScreen, offline adapter, deletion, and shutdown remain open. |

The 10 skipped tests are not counted as passes; private-material gates cannot run in this synthetic-only exercise. The three warnings in the full suite were one Starlette test-client deprecation, one pytest class fixture warning, and one deliberately duplicated ZIP member warning. The exact source branch was confirmed in the validation log as an editable install from the isolated worktree. An earlier browser failure and first ad hoc full-suite result came from a test venv bound to the older PR worktree; they are retained in notes as diagnostic evidence and are not counted as frozen-source results.

| Exact local command | Exit | Evidence |
| --- | ---: | --- |
| `./scripts/validate_offline_linux.sh` | 0 | `exact_linux_build.log`, `exact_linux_build.exit` |
| `PYTHONPATH=/home/soroush/njit-thesis-auditor/worktrees/offline-desktop-release-readiness-20261016/src /tmp/njit-offline-validation-1000/bin/python -m pytest -q` | 0 | `final_full_pytest.log`, `final_full_pytest.exit` |
| `TMPDIR=/home/soroush/snap/firefox/common/njit-selenium-tmp /tmp/njit-offline-test-venv/bin/python /home/soroush/njit-thesis-auditor/notes/offline_desktop_release_readiness_20261016/packaged_browser_smoke.py` | 0 | `release_packaged_browser_smoke.log`, `.exit` |
| `/tmp/njit-offline-validation-1000/bin/python scripts/smoke_offline_linux.py 'dist/NJIT Thesis Auditor' --trace /home/soroush/njit-thesis-auditor/notes/offline_desktop_release_readiness_20261016/release_linux_trace` | 0 | `release_linux_smoke.log`, `.exit`, `release_linux_trace.*` |
| `unshare -Urn true`; `bwrap --unshare-net --ro-bind / / --dev-bind /dev /dev --proc /proc -- /usr/bin/true` | 1 each | `checkpoints.md`; namespace creation denied by host |
| `powershell -ExecutionPolicy Bypass -File scripts/build_offline_windows.ps1` | NOT TESTED | No native Windows host/VM or PowerShell available |

## Reproduction and remaining release gates

On Linux x64 with Python 3.12, from the isolated branch run `./scripts/validate_offline_linux.sh`. It installs from `packaging/offline-build-constraints.txt`, runs Ruff, mypy and relevant tests, builds the native one-folder package, inspects it, and exercises the packaged executable. The additional full suite used `PYTHONPATH=<isolated-worktree>/src /tmp/njit-offline-validation-1000/bin/python -m pytest -q`. The local browser helper and strace paths are listed in the dated notes.

On **native Windows x64**, use a clean committed worktree and run `powershell -ExecutionPolicy Bypass -File scripts/build_offline_windows.ps1`, then complete **every** gate in [the Windows acceptance checklist](../implementation/offline_windows_acceptance.md). Record the complete folder hash, clean-profile browser screenshots, network trace, local profile ACL/deletion observations, process/listener shutdown, and test exit codes. Review application traffic separately from browser, extension, and operating-system traffic. Resolve any native failures and obtain an explicit Windows release review before distribution. Until then the Windows application is **not genuinely ready for Ester**.

The application cannot remove browser history, extension caches, synced-profile copies, browser download folders, operating-system backups, or reports a user saved outside its managed directory. Tests here do not establish secure disk erasure or certify confidentiality.
