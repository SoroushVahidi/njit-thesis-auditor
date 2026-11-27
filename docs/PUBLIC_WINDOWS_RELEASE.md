# NJIT Windows beta release

Published bytes, exact source pin, build run and actual test limits: [rc.3 release record](releases/windows-0.2.0-rc.3.md). This document is the build/publication procedure; current source changes do not replace the published executable.

The rc.3 release task authorized public installer distribution, integration and
deployment. That historical authorization does not authorize a future release or
deployment merely because this procedure is available or checks pass.
Keep `SoroushVahidi/njit-thesis-auditor` private. Only the selected installer,
its byte metadata/checksum and brief release documentation belong in the separate
public distribution repository `SoroushVahidi/njit-thesis-auditor-desktop`.
Never copy a source checkout, Git history, credentials, student PDFs or audit outputs
into that repository.

## Recovered source and new build

**Historical rc.3 context:** the source history and versioned commands below
document rc.3. For a future authorized release, use a new version and record its
own source and validation;
never overwrite the published rc.3 bytes. For development worktree and output
conventions, see the [development guide](DEVELOPMENT.md).

The release branch starts from `7069363583ddeafc910f91c62c0845cc415b7bd0`, which
includes the Windows loopback, concurrent PDF publication and UTF-8/LF export fixes.
It adds PowerShell 5.1 quoting corrections, stable GET redirects for failed
submissions, report badge/navigation/terminology corrections, local completion time,
Audit IDs under Technical details, and active-audit recovery during navigation.
Bundled Help/Rule Reference and the existing worker are retained. Rules, thresholds,
raw findings and machine-readable export schemas are unchanged.

The requested final Windows commit `93457c10b18d59e829a97a72b6215123c150ee51`
was unavailable from GitHub and the Ubuntu project handoffs at recovery time.
The recorded `0.2.0-rc.2` installer was not recovered or substituted. Its recorded
size is 41,335,510 bytes and SHA-256 is
`19266ec1b7bfd375afeee16a65eb732897f617ca46070cc3902d55bb06f2f883`.

The replacement is a **new build, version 0.2.0-rc.3**, with its own source SHA,
size and checksum. Do not claim byte identity or inherit earlier test results.

## Build and smoke checks

`.github/workflows/windows-desktop.yml` defaults to the hosted `windows-2025`
runner. Explicit dispatch can select a self-hosted Windows 11 runner for native
qualification. The workflow checks out the actual PR source head when run on
a pull request, installs isolated tools, runs focused native
regressions, executes the established packaging script through **Windows PowerShell
5.1**, and runs a packaged startup/synthetic audit/export/Help/Rules/shutdown smoke
check. Installer/uninstaller lifecycle qualification is not a publication gate.
The workflow uploads the installer, checksum, metadata and test evidence as private
Actions artifacts; those expiring URLs are not public download destinations.

The build script emits:

```text
dist/installers/NJIT-Thesis-Auditor-Setup-0.2.0-rc.3.exe
dist/installers/NJIT-Thesis-Auditor-Setup-0.2.0-rc.3.json
dist/installers/SHA256SUMS.txt
```

These paths describe expected output, not completed build evidence. Read the actual
metadata and independently recompute the EXE checksum before selecting it.
A Windows Server smoke check does not establish clean Windows 11 qualification,
installer/uninstaller behavior or every prior test result. State those limits in
the beta release notes, along with actual source SHA, version, size and SHA-256.
Windows 11 x64 remains the installer target; do not advertise Windows 10 support.

## Publish and enable

Use a fresh distribution-only repository if it does not exist. Publish the exact
selected EXE at this durable HTTPS URL:

```text
https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/download/desktop-v0.2.0-rc.3/NJIT-Thesis-Auditor-Setup-0.2.0-rc.3.exe
```

Publish brief beta release notes and the actual checksum/metadata. Do not replace
published bytes under an existing version. Verify an anonymous download with TLS,
HTTPS redirects, an executable response beginning `MZ`, exact byte count and
SHA-256 before enabling the link.

After checks pass, merge the release PR normally, respecting any branch protections.
Use the exact merged main commit and the established dedicated systemd deployment
worktree described in [DEPLOYMENT.md](DEPLOYMENT.md). Preserve existing service
settings and access controls. Set these deployment fields together; each has prefix
`NJIT_AUDITOR_WINDOWS_DOWNLOAD_`:

| Suffix | Value |
| --- | --- |
| `APPROVED` | `1` (authorized public distribution) |
| `BETA` | `1` (beta publication, independent of lifecycle qualification) |
| `EDITION` | `njit` |
| `URL` | Exact versioned HTTPS EXE URL |
| `SHA256` | Actual 64-character installer SHA-256 |
| `SIZE_BYTES` | Actual positive byte count |
| `ARCHITECTURE` | `x64` |
| `WINDOWS_VERSIONS` | `Windows 11` |

Restart only `thesis-auditor-web.service`. Verify `/version` matches the deployed
main commit, `/healthz` succeeds, the enabled **Download for Windows (Beta)** link
is visible, its actual target downloads anonymously with matching size/checksum,
and a fresh synthetic website audit and report download succeed. Test Help/Rules.
Setting `APPROVED=0` and restarting withdraws the link without changing access.
