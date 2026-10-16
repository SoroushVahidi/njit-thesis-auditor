# Offline desktop auditor

The desktop edition runs the existing PDF audit and student report interface on the user's computer. It serves only `127.0.0.1` on an available port. The browser opens through a per-launch ticket; all subsequent routes require that session. Uploads and reports use the same audit engine and report builders as the online app. The desktop route table excludes URL fetching, built-in private samples, health/version APIs, and OpenAPI. FastAPI telemetry, including environment-triggered exporter setup, is disabled for this app.

## Use

On a supported built platform, extract the entire **NJIT Thesis Auditor** folder and double-click **NJIT Thesis Auditor.exe** on Windows (or **NJIT Thesis Auditor** on Linux). No Python installation or terminal is required for users. Select a PDF in the opened browser page. Use **Quit** in the page when finished. If Tcl/Tk is available, a small launcher window also offers **Open auditor** and **Quit**; browser mode works without it. The server exits after 30 minutes without an authenticated request when no audit is running, or after the eight-hour session expires. Keep the full one-folder distribution together.

The app's temporary data lives under `%LOCALAPPDATA%\NJIT Thesis Auditor` on Windows and `$XDG_DATA_HOME/njit-thesis-auditor` (or `~/.local/share/njit-thesis-auditor`) on Linux. Audit work is under `audits/`; multipart upload spool files use the private `tmp/` directory. The application makes its own root private to the user where supported. **Delete this audit** removes one finished audit, **Delete all local audit data** removes finished audits and queues active ones for deletion after they finish, and Quit clears temporary work. A failed deletion is shown in the interface and can be retried. Startup clears abandoned audit work from a prior interrupted run. Reports saved through the browser outside that directory remain under the user's control. This is ordinary file deletion, not secure disk erasure.

The browser, OS, browser extensions, or a synced profile can have their own behavior outside the application's control. The application itself does not upload the original PDF or call a remote API. The service requires a per-launch session cookie established with a ticket, validates Host and Origin, blocks cross-site requests, requires CSRF tokens for mutations, and expires the session after eight hours. Session secrets stay in process memory and are not included in reports.

## Build from source

Use a clean **Python 3.12 x64** environment on the target operating system. PyInstaller does not cross-compile a Windows executable from Linux. These commands are for builders; end users run the packaged application directly.

```bash
python -m venv .venv-build
.venv-build/bin/python -m pip install -c packaging/offline-build-constraints.txt -e . pyinstaller
.venv-build/bin/pyinstaller --noconfirm --clean packaging/offline_desktop.spec
```

On Windows PowerShell, replace `.venv-build/bin/` with `.venv-build\Scripts\`. The output is `dist/NJIT Thesis Auditor/`; distribute the whole folder after validation. The spec explicitly includes six shared HTML templates used offline, the offline upload template, the rule catalog, Ester's warning wording map, and a redistributable DejaVu font with its license. The original online index, dissertations, private samples, evaluation ledgers, private notes, credentials, and repository history are not included as data. The Python runtime and PDF libraries are collected from the clean build environment. Inspect the final artifact and run the packaged smoke check on each target operating system before distribution.

For development without packaging, install the project and run `python -m njit_auditor.offline_launcher`; the launcher opens the browser and stays alive until Quit. `--headless` and `--no-browser` exist only for automated smoke testing.

## Validation scope

The native Linux one-folder build was exercised with a synthetic PDF: unauthorized requests were rejected, a local upload completed, report and highlighted PDF routes returned 200, and Quit left no listener or temporary audit files. A syscall trace showed only a bind to `127.0.0.1` and no non-loopback connects by the traced application. In-process tests completed an audit with outbound socket connects disabled. Linux network namespaces were unavailable on the workstation (`unshare -n`: operation not permitted), so a real disabled-network namespace test remains open. These checks do not certify confidentiality.

Online/offline parity tests use normal, Unicode, rotated, and low-text synthetic PDFs on the same source revision. They compare normalized JSON and Markdown, text reports, student-card data, PDF report text and drawings, original and highlighted PDF pages, and sorted/filterable HTML data. Job IDs, timestamps, and local file paths are the only normalized fields. Detector thresholds and rule IDs are unchanged.

**Platform status:** Linux x64 development build validated. Windows x64 spec and build instructions prepared; the Windows executable, installer experience, antivirus behavior, and native Windows launch/storage behavior remain untested until a Windows build and review. Do not distribute this candidate to Ester yet.

## Candidate validation record (2026-10-16)

The portable code at `7f6b165` passed Ruff (exit 0), mypy on 149 source files (exit 0), and the full local suite (4,769 passed, 10 private-material skips, 3 warnings; exit 0). The focused offline/web/report suite passed 374 tests (exit 0). The Linux x64 one-folder executable was rebuilt from that code and its launcher SHA-256 is `849b7e5cd5910cf18aa1a86150df73b4837c590c6f284be2f4ffbe5195cc1a05`; the binary is only one part of the 132 MB folder. Independent review: **APPROVE** for portable implementation and Linux development build, with Windows untested. A real browser interaction pass for the filter controls and a native Windows build remain before end-user distribution.
