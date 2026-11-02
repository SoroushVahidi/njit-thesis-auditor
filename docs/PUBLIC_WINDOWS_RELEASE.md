# Full NJIT Windows application release

The user has authorized distribution of the full NJIT rule implementations and
accepted inspectable packaged files/rules. PyMuPDF licensing is resolved. Neither
is a release blocker. The source repository remains private; only qualified
installer assets and reviewed release documentation will be public.

## Implementation

Candidate application: **NJIT Thesis Auditor 0.2.0-rc.2**, Windows 11 x64 target.
Windows 10 is not advertised or accepted by this installer pending validation.
The production reference is `4efd780dde53eea907a714df8bfed86e923ef86a`.
See [the complete feature/rule matrix](WINDOWS_FEATURE_PARITY.md).

The existing authenticated FastAPI/local-browser desktop is integrated with the
production engine and reporting templates. No detector thresholds or rule IDs
were changed. All rule modules, rule JSON, wording, templates, fonts, icon and
Python runtime are bundled. URL imports have a local equivalent: save the PDF
and upload it. Built-in examples use a locally generated synthetic PDF instead
of distributing private student samples. Help and Rule Reference are local.

The launcher disables Uvicorn's console-dependent logging configuration so a
windowed Windows executable can start with stdout/stderr absent. Audits run in
supervised processes with native Windows Job Object containment; Cancel, Quit,
reopen, bounded shutdown and temporary cleanup reuse the existing implementation.
The launcher and workers deny outbound Python socket connections. Browser UI
requests remain on loopback; sending email via the contact link requires connectivity.

## Build and validate

On native Windows x64, use Python 3.12 x64 and Inno Setup 6 **on the builder only**:

```powershell
./packaging/build_offline_windows.ps1
```

The script verifies a clean committed checkout, installs pinned build dependencies,
creates the full NJIT one-folder application, checks all rule modules/resources,
and compiles `packaging/windows_installer.iss`. Candidate output:

```text
dist/installers/NJIT-Thesis-Auditor-Setup-0.2.0-rc.2.exe
dist/installers/NJIT-Thesis-Auditor-Setup-0.2.0-rc.2.json
dist/installers/SHA256SUMS.txt
```

These are **output paths, not evidence that an installer has been built**.
The JSON records exact installer bytes/hash/size/source and defaults qualification
and publication flags to false. No checksum or size is invented before building.
The graphical installer offers a custom directory, Start Menu shortcut, optional
desktop shortcut, automatic launch, version/icon and standard uninstaller. No
student Python installation or terminal is part of the intended install flow.

`.github/workflows/windows-desktop.yml` runs the native build, bundle inventory,
synthetic regressions, production-reference capture, interactive installation to
a path with spaces/Unicode, first launch, parity, reopen, cleanup and standard
silent uninstallation. It blocks the installed application's outbound traffic and
keeps the test driver and runner online. Only explicit candidate/evidence files
are uploaded as **private CI artifacts**. No source checkout is published.

The default `windows-2025` runner is Windows Server, not Windows 11. Its pass
cannot qualify Windows 11. The manual workflow also supports a registered
`[self-hosted, Windows, X64, windows11]` interactive runner. The clean-client
qualification still requires a Windows 11 x64 machine without Python/developer
tools: install graphically, test the chosen path and shortcuts, disconnect the
OS network, audit/export/view original and annotated PDFs, open Help/Rules, Quit,
reopen and uninstall through Windows Settings. Preserve exported user files.
Record OS build, source commit, installer SHA-256, screenshots and each result.

Before this workflow is merged to the default branch, run it by pushing a normal
commit to the open PR #640 branch (without `[skip ci]`). The `pull_request`
`synchronize` event runs the branch's workflow even while the PR is a draft;
`gh workflow run` cannot dispatch a workflow that is not registered on main.
The existing Linux CI selects synthetic tests and skips LFS downloads for this
candidate branch only. Other branches retain the full regression suite. Both
native and Linux candidate suites include the desktop worker/lifecycle tests.
If Actions rejects the run before assigning a runner, retain the run URL and
check annotations; a queued workflow or successful push is not a native pass.

Parity capture checks `/version` against the authoritative SHA, then uses six
nonconfidential PDFs. Comparisons retain IDs, severity, locations, explanations,
card text, grouped-route status/content, original bytes, report content, drawing
geometry and PDF annotations. Only volatile job IDs/paths/timestamps and float
serialization noise are normalized. Help comparisons retain all explanation
sections except the explicit local/server-processing introduction. Existing
production 404 group links are recorded as 404, not mislabeled as working links.

## Publish only after qualification

Keep the source repository private. Use the separate public distribution-only
repository `SoroushVahidi/njit-thesis-auditor-desktop`, with fresh history containing
only release documentation and approved assets. Publish the tested EXE under:

```text
https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/download/desktop-v0.2.0-rc.2/NJIT-Thesis-Auditor-Setup-0.2.0-rc.2.exe
```

This is a **proposed URL, not a verified download**. Publish a new version for each
change; never replace approved bytes. Check the final installer for unintended
student data, credentials, private logs and repository history. The NJIT rule
implementations themselves are intentionally included.

Download anonymously from an independent browser/network with TLS verification.
Verify every redirect uses HTTPS, the response is the actual EXE with attachment
filename/binary content type, and its exact size/SHA-256 match the final release.
If signing changes bytes, regenerate metadata and retest the final installer.

## Enable the existing homepage section

The homepage title is **Download NJIT Thesis Auditor for Windows**. The existing
PR #640 configuration defaults to disabled; no URL is exposed while unqualified.
The enabled card displays version, Windows 11/x64, bytes/MiB, installation steps
and SHA-256. All fields below have prefix `NJIT_AUDITOR_WINDOWS_DOWNLOAD_`:

| Suffix | Value |
| --- | --- |
| `APPROVED` | `1` only after native and anonymous-download qualification |
| `EDITION` | `njit` |
| `NATIVE_TESTED` | `1` backed by the exact installer qualification |
| `URL` | Exact versioned HTTPS EXE URL |
| `SHA256` | Exact 64-character installer SHA-256 |
| `SIZE_BYTES` | Actual positive byte count |
| `ARCHITECTURE` | `x64` |
| `WINDOWS_VERSIONS` | `Windows 11` |

The retired confidentiality flag is not required. Release flags record evidence;
they do not prove tests happened. Requests cannot configure these settings.

After review and passing required checks, squash-merge PR #640 and follow
[DEPLOYMENT.md](DEPLOYMENT.md) using the exact clean merged main SHA. Set release
metadata together in the existing systemd service environment, restart only that
service, verify `/version`, and test the live desktop/mobile download and synthetic
auditing workflow. Withdraw the link by setting `APPROVED=0` and restarting that
service. No activation or deployment occurs merely by committing this code.
