# Desktop integration and download preparation

The candidate combines student PR #634 (`efed063`) with desktop PR #620
(`ae0d00b`) and its integration/security review #621 (`c4ad543`). The local
integration commit preserves both ancestry paths. It reuses the existing
loopback FastAPI launcher, session/Host/Origin/CSRF protections, PDF engine,
reports, and cleanup. No detector thresholds or anonymizer behavior change.
The report-boundary and exception-class-only logging fixes are inherited from
#621; they affect shared report routes and are deliberately retained here.
No production changes are applied by preparing this branch.

Real Chromium testing additionally exposed an inherited browser-only failure:
`no-referrer` on every page caused form POSTs to send `Origin: null`, which the
correct origin guard rejected. The ticket redirect retains `no-referrer`;
authenticated pages now use `same-origin`. Host, Origin, session, and CSRF
checks remain strict. The browser regression submits actual forms. A focused
skip link also now overlays the page, avoiding a layout shift that could make
the next mouse click miss its target after keyboard navigation.

## Student package

The planned package is `NJIT-Thesis-Auditor-0.2.0-rc.1-windows-x64.zip`.
It is a portable one-folder distribution: Extract All, then double-click
`NJIT Thesis Auditor.exe`. No Python, terminal, administrator installation,
or internet access is needed for auditing. The default browser displays the
local student interface. Quit in the page or launcher stops the service;
closing only the browser tab does not. The launcher window's close button
also requests shutdown. The existing idle/session limits remain.

Target platforms are Windows 10 and Windows 11, x64. These are targets, not
claims of completed native qualification. Windows ARM64, 32-bit Windows, and
macOS are not qualified. Linux x64 is used only for development validation.
The student guide and release notes are `packaging/READ-ME-FIRST.txt` and
`packaging/DESKTOP-RELEASE-NOTES.txt`; the Windows builder includes both.

## Native build and package

On a clean, committed checkout on native Windows x64 with Python 3.12 x64:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_offline_windows.ps1
```

This developer command creates a fresh build environment, installs the pinned
constraints, runs the allowlisted PyInstaller spec, and prepares the portable
ZIP. The spec includes About and the current shared finding templates, font
and license, application icon, Windows version resource, and build provenance.
The Windows-specific dynamically imported lock module is included explicitly;
PyInstaller's Windows-only pefile and pywin32-ctypes dependencies are also pinned.
It excludes private samples, raw documents, repository history, and the URL
fetcher. The packager refuses a non-Windows host or a non-x64 PE launcher.
Neither a mocked PE test nor a Linux bundle satisfies native verification.
PyInstaller requires building on the target OS:
[official operating-mode documentation](https://pyinstaller.org/en/stable/operating-mode.html).

`dist/packages/` receives the versioned ZIP, its SHA-256 file, and a candidate
JSON containing the measured byte size, archive checksum, and source commit.
These are generated from actual bytes; no Windows size or checksum is supplied
before a build. Existing ZIPs are not overwritten. Run the complete
[native smoke checklist](offline_desktop_windows_smoke.md), including actual
Windows 10/11, no-Python launch, networking disabled, ACLs, antivirus behavior,
shutdown, and clean-machine testing. Do not publish this candidate on the
strength of Linux checks.

## Disabled website feature

`config/desktop-release.json` defaults to `enabled: false` and `preview: false`.
The public website therefore renders no download button or installer link.
An unavailable `/desktop` returns 404. For a local visual review only,
`preview: true` renders a disabled **Download Desktop App** button and:
“Audit your thesis locally, even without internet access.” It supplies no
installer URL. Desktop mode excludes the download route and never advertises
web downloads.

The [dependency licensing review](desktop_license_review.md) is also a release
gate; copying notices alone does not authorize distribution.

A visible link requires all of: a versioned allowed HTTPS URL, valid SHA-256,
positive measured size, native build verification, recorded native tests for
every advertised Windows version, anonymous public-download verification and
timestamp, explicit licensing review/basis, distribution approval, and enablement. The site reads only
this static record; it does not make verification requests during page loads.

## Proposed public hosting

Use GitHub Releases in a **separate public binary-only distribution repository**,
proposed name `SoroushVahidi/njit-thesis-auditor-desktop`. Keep the existing
source repository private. This task does not create the distribution repository,
change visibility, publish a release, or claim a proposed URL exists.
GitHub documents [versioned release links](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases)
and [anonymous access for public release resources](https://docs.github.com/en/rest/releases/releases).

The proposed URL pattern, for future use after approval, is:

```text
https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/download/desktop-v<VERSION>/NJIT-Thesis-Auditor-<VERSION>-windows-x64.zip
```

It is intentionally absent from the enabled website configuration. After an
approved artifact is publicly hosted, copy its actual URL into its candidate
manifest and run the verifier without GitHub credentials:

```bash
python scripts/verify_desktop_download.py candidate.json --receipt verified-download.json
```

The verifier downloads anonymously over HTTPS, permits only the expected
GitHub asset redirect hosts, and compares the complete bytes, size, and SHA-256.
Its receipt still disables the button and clears distribution approval. A
separate reviewed configuration change records native test evidence and
approval before any website enablement. A private, missing, or mismatched asset
cannot produce a successful verification receipt. The verifier does not upload
or publish anything.

## Versioning and updates

`desktop_metadata.py` owns the desktop version and four-part Windows file
version. Use a new version/tag/filename for each distributed package, retaining
its checksum, build SHA, dependency freeze, native test record, and release
notes. Rebuilding creates a new candidate whose bytes must be verified again;
never substitute a different file under an already approved release record.
Updates are manual, full-package downloads into a new directory after Quit.
There are no automatic update requests, remote document APIs, or telemetry
exporters in the desktop app's tested path.

## Storage and remaining limits

Local data is under `%LOCALAPPDATA%\NJIT Thesis Auditor` (`audits` and `tmp`)
on Windows, and `$XDG_DATA_HOME/njit-thesis-auditor` or
`~/.local/share/njit-thesis-auditor` on Linux. Working files are deleted on
normal Quit, with abandoned data cleared at startup. Saved browser downloads
remain user-managed; deletion is not secure erasure. Existing link/junction
and report path guards remain. Native Windows ACL/junction behavior is still
a required verification gate.

Desktop audits now use a killable process supervisor with a 120-second
deadline, cancellation, and process-tree cleanup. See
[bounded desktop execution](desktop_bounded_execution.md). The hosted web
execution policy is unchanged.
The inherited IPv4-mapped IPv6 URL validation issue is unreachable through the
desktop route table, which has no URL-import endpoint; it remains a separate
web deployment issue. The inherited #621 PDF failure-log fixes are retained,
not treated as a newly completed production deployment. Browser/OS telemetry,
extensions, and exported files are outside the app's session boundary.


## Verification performed during this preparation

The integrated source's real local-launcher/Chromium checks passed at 390 and
1440 pixels, including all eight corrected student actions, About, keyboard
controls, filters, highlights, exports, repeated audits, deletion, corrupt-PDF
recovery, and Quit. The download preview is disabled and has no installer link.

The pure Windows version-resource parser/serializer was checked on Linux with
the unavailable native API stubbed out; this does not test native embedding. A clean pinned Linux x64
PyInstaller build was also exercised with Python
absent from PATH. Four synthetic fixture types matched the same source
revision's web auditor for normalized JSON, Markdown, text, and PDF reports.
Its traced application run bound only 127.0.0.1, recorded no connect syscalls,
rejected unauthorized HTTP access, and cleared working files and its listener
on Quit. Bundle names and archive module listings excluded the private/sample
and URL-fetch modules; this is an inventory check, not a confidentiality proof
for arbitrary bytes. The archive is marked Linux DEVELOPMENT only, is kept
outside Git, and is not a Windows build or approved public release.

Source audit tests denied application socket/DNS calls; the browser harness
blocked external requests. A genuine disabled-network namespace was unavailable
(permission denied), so OS-level disconnected-network verification remains
open. Tcl/Tk was absent from the Linux build environment, so its browser fallback
was exercised. Windows GUI controls, clean Windows machines, ACLs/junctions,
and Windows network behavior remain unverified. No production service was
contacted for document processing, deployed, or restarted.
