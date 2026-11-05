# Offline desktop auditor

## Install and use the published Windows beta

Download **Windows Beta 0.2.0-rc.3** from the
[public downloads/releases repository](https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/tag/desktop-v0.2.0-rc.3).
Verify its size and SHA-256 against the [release record](../releases/windows-0.2.0-rc.3.md),
then run `NJIT-Thesis-Auditor-Setup-0.2.0-rc.3.exe`. Launch NJIT Thesis Auditor
from the installed shortcut. Users do not need Python or a terminal.
Windows 11 x64 is the target; clean Windows 11 and installer-lifecycle qualification
remain unperformed. The published beta's actual hosted test limits are in the release record.

The app opens a browser interface served on `127.0.0.1` at an available port.
The current shared source accepts uploaded PDFs only. Select a PDF, or choose
**Download sample PDF**, save it, and select the saved file. The published rc.3
installer retains its original **Audit synthetic example** shortcut until a new
version is built; this task does not rebuild Windows. Help and Rule Reference are
bundled locally. Use **Quit** when finished. If the launcher window is available,
it also offers Open auditor and Quit. The application's audit processing is local;
the browser, extensions and operating system have their own behavior.

Temporary Windows data is under `%LOCALAPPDATA%\NJIT Thesis Auditor`, with audits
under `audits/` and upload spool files under `tmp/`. Delete controls remove local
audit data; reports saved elsewhere remain under the user's control. This is
ordinary deletion, not secure erasure. The local service uses a per-launch session,
Host/Origin validation and CSRF checks. Source development on Linux uses
`$XDG_DATA_HOME/njit-thesis-auditor` or `~/.local/share/njit-thesis-auditor`.

## Current source versus rc.3

[PR #645 wording](../STUDENT_WORDING_USABILITY.md),
[About Us and PR #647's acknowledgment correction](../ABOUT_US_CONTENT.md) are
implemented in the website/shared desktop source and await another installer.
The shared source also includes **Download Comments PDF**, a standalone comments-only
PDF using the same findings and wording as the legacy text export. It generates
locally with network connections blocked and includes findings without highlights.
The Complete PDF Report remains separate and unchanged. These changes will appear
in the next desktop build; no Windows installer was rebuilt or published for this change.

They are not retroactively added to rc.3. Current source bundles seven shared
HTML templates, including About Us, plus the local upload page, rule resources,
font and license. Source About renders without automatic external requests;
email/release links need connectivity only when deliberately opened.
These source-template/simulated-bundle checks do not test the published executable.

The desktop route table excludes URL fetching, private built-in samples, the
website health/version APIs and OpenAPI. Original online templates, student PDFs,
evaluation ledgers, private notes, credentials and Git history are excluded from
the package data allowlist. Inspect each future bundle and record its own source
SHA, version, checksum and test results.

## Develop and build from private source

Use a private authorized checkout. `pyproject.toml`'s Python package version
`0.1.0` is separate from the desktop installer version `0.2.0-rc.3`.
For source development:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,browser]"
python -m njit_auditor.offline_launcher
```

The packaged build uses **Python 3.12 x64 on the target operating system**;
PyInstaller does not cross-compile Windows from Ubuntu. The established hosted
Windows workflow and exact PowerShell 5.1 command are documented in
[Windows publication](../PUBLIC_WINDOWS_RELEASE.md). On native Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging/build_offline_windows.ps1
```

For a Linux development bundle:

```bash
python -m venv .venv-build
.venv-build/bin/python -m pip install -c packaging/offline-build-constraints.txt -e . pyinstaller
.venv-build/bin/pyinstaller --noconfirm --clean packaging/offline_desktop.spec
```

`dist/NJIT Thesis Auditor/` is the one-folder application bundle; keep it together
when testing a portable build. The Windows build also produces an installer under
`dist/installers/`. Neither output is a new release until selected, versioned and
published separately. Do not run another Windows build for documentation changes
or overwrite rc.3. A future installer must use its own version and checksum.

## Validation records and remaining checks

Use [reproducibility](../REPRODUCIBILITY.md) for source/browser tests,
[the release record](../releases/windows-0.2.0-rc.3.md) for completed hosted Windows
checks, and [the native checklist](offline_desktop_windows_smoke.md) for broader
unperformed Windows 11, lifecycle, storage, network and manual GUI qualification.
These are different kinds of evidence; a source test does not establish native
installer behavior. Historical reviewer checks are not release approval.

## Candidate validation record (2026-10-16)

The dated candidate record and original Linux validation scope moved to [Linux desktop validation — 2026-10-16](history/offline_desktop_linux_validation_20261016.md).
Their source SHA, counts, checksum, context and limits are preserved there.
