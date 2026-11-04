# Native Windows x64 desktop smoke checklist

Run this on a genuine Windows x64 machine with Python 3.12 x64 for the build. Record the Windows version, build host, repository SHA, executable SHA-256, each result, and paths to private synthetic evidence. Linux and Wine runs do not satisfy this gate.

## Build and inspect

1. Start from a clean checkout of the exact candidate SHA. Run `powershell -ExecutionPolicy Bypass -File packaging/build_offline_windows.ps1` from the repository root. Record the complete build log and final `Get-FileHash` output.
2. Keep the complete `dist\NJIT Thesis Auditor` folder together. Search all bundled names and text resources for private samples, review ledgers, credentials, `.git`, source PDFs, and unexpected environment files. Confirm the expected templates, rule catalog, wording map, font, and font license are present. Record file count and total size. Do not attach private content to the report.
3. Run `ruff check .`, `mypy src`, and `python -m pytest -q` on the same SHA. Record exact versions and counts. Do not substitute a Linux test result.

## Launch and process lifecycle

Run manual GUI checks and automated installer/parity validation **sequentially**.
Before each phase, record its executable, PID, data profile and loopback port (never
the launch ticket). Finish/export any active audit and quit that phase's launcher
before continuing. Do not close someone else's session automatically. Installer and
packaged parity validation refuse to start while an Auditor process is running.
The installer harness deselects its final automatic launch; parity owns one native
launcher and a fresh Chromium cookie store, without opening the default browser.
Wait for its verified shutdown before reopening. Separate `LOCALAPPDATA` directories
deliberately permit separate instances and do not test same-directory exclusion.

4. Set `LOCALAPPDATA` to a disposable, user-owned test directory. Launch the packaged `.exe` normally. Confirm the browser opens at `http://127.0.0.1:<random-port>/`, the ticket URL redirects without retaining the ticket in the address bar, and the interface works with and without Tk available.
5. Use `Get-NetTCPConnection` to confirm the process listens only on `127.0.0.1`. Confirm no listener on `0.0.0.0`, a LAN address, or IPv6. With a packet capture or firewall log covering the process, exercise launch, upload, report generation, and shutdown; record any DNS queries or outbound connections. Disable networking and repeat the synthetic audit.
6. Start a second packaged instance using the same data directory. It must exit with the single-instance warning without clearing the first instance's audit. Confirm the first instance remains usable.

## Synthetic audit and interface

7. Upload synthetic normal, Unicode, rotated, low-text, malformed, encrypted, and oddly named PDFs. Record accepted/rejected states and compare normal cases with the online app on the same SHA: finding IDs and counts, pages, boxes, JSON, Markdown, text and combined PDF reports, original and highlighted PDFs, problem cards, sort/filter controls, and navigation links.
8. For a completed job, open every report and PDF route. Confirm the viewer, download filenames, highlights, page controls, filters, and sorting work in a real browser. Check that errors for malformed and encrypted PDFs show no path or exception details.
9. Without the session cookie, request the index, job page, original PDF, highlighted PDF, and each report URL. Each must deny access. Test wrong Host, wrong Origin, cross-site `Sec-Fetch-Site`, missing Origin on POST, missing/wrong CSRF, invalid ticket, and expiration. Confirm mutation routes reject unauthorized requests.
   Cancel both a pending and a running synthetic audit. Each must reach an **Audit
   canceled** page, retain its browser session, keep Help/Rule Reference available,
   and allow a new audit. Invalid-session browser navigation must display recovery
   instructions with HTTP 403; API requests must retain JSON errors. In a separate,
   explicitly isolated regression, run two disposable profiles on different ports
   in one browser cookie store and verify each session survives opening the other.
   Close both test processes before resuming manual qualification. The native
   `tests/test_windows_startup.py` same-directory test checks that rejection leaves
   the first audit and temporary-work sentinel intact; it does not replace the
   packaged executable qualification above.
10. Try URL-encoded traversal in job IDs and report paths and a symlink or junction pointing from `audits` or `tmp` to a disposable sentinel directory. Also link `desktop.lock` to an empty disposable outside file and confirm startup refuses it without writing to that file. Confirm outside files survive and startup refuses linked storage. Use only disposable synthetic data.

## Data and shutdown

11. Inspect `%LOCALAPPDATA%\NJIT Thesis Auditor\audits` and `tmp` during processing. Confirm files stay in the app directory and inspect their ACLs with `icacls`. Check two concurrent synthetic uploads and deletion while one audit is running.
12. Use **Delete this audit** and **Delete all local audit data**. Confirm report/PDF URLs stop working, workspaces disappear, and a simulated failed deletion is visible and retryable. Leave an interrupted synthetic workspace, relaunch, and confirm startup cleanup.
13. Use **Quit** and close the launcher window separately. Confirm the process and listener exit and `tmp` and audit workspaces are cleared. Exercise the 30-minute idle and eight-hour session expiry on a test host or with controlled clock constants. Check Task Manager for lingering child processes.
14. Inspect application logs, crash output, browser responses, and bundled resources for synthetic PDF text, file paths, job IDs, ticket, cookie, and CSRF token. Record any leaks and redacted evidence.

Mark the Windows gate PASS only after the packaged executable passes these steps on native Windows x64. Preserve detailed logs outside Git; summarize results and remaining limits in the release readiness report.
