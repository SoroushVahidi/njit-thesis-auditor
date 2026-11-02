# Windows homepage download release gate

The homepage includes **NJIT Thesis Auditor — Windows Desktop Application**.
Downloads default to disabled, with no URL or invented release metadata. The
online upload, Help, Rule Reference, auditing and reporting paths stay intact.

## Current release decision (2026-11-02)

Activation is blocked. GitHub main and the production checkout were verified at
`4efd780dde53eea907a714df8bfed86e923ef86a`. No Windows installer or native Windows
qualification report was located in repository releases or the relevant local
desktop artifact folders. The private desktop candidate is version `0.2.0-rc.1`,
targeting Windows 10/11 x64; those targets are **not verified platform support**.
The historical proposed `NJIT-Thesis-Auditor-0.2.0-rc.1-windows-x64.zip` was never
built in the available records and is not a graphical installer. There are no
verified Windows bytes, file size, checksum or public download URL to configure.

The generic **Document Format Auditor** is a different edition. No generic
installer was located or substituted. It must not be presented as the full NJIT
application. Full parity with the current online application is not established
by older same-revision Linux comparisons.

The private NJIT packaging recipe at desktop commit
`8d7a014bfee1df640731fda22963b9f28389f3aa` includes
`data/processed/rules/project_added_rules.json`, wording resources, and a
PyInstaller PYZ containing Python modules used by the audit engine. Recipients
can inspect packaged resources and bytecode. Publicly distributing that full
offline bundle therefore conflicts with the requirement to keep private NJIT
rule implementations confidential. A private source repository or executable
wrapper does not resolve that conflict. Do not publish this candidate. A release
architecture that satisfies confidentiality and offline functionality is still
required; setting an approval flag cannot make the existing bundle confidential.

PyMuPDF licensing is resolved for this task and is not an outstanding gate.

## Distribution contract

Use a separate public distribution repository with fresh history containing only
reviewed public release documentation and qualified binary assets. Never mirror
the private repository, its history, private rules, samples, logs or credentials.
The allowlisted HTTPS contract is:

```text
https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/download/desktop-v<VERSION>/NJIT-Thesis-Auditor-Setup-<VERSION>.exe
```

This is a proposed contract, **not an existing asset**. The matching tag and
filename are versioned; the application rejects mutable `latest` URLs, private
source-repository URLs, HTTP, arbitrary hosts, queries and fragments. Publish a
new version for every change; never replace bytes at an approved URL. GitHub
must serve the binary as an attachment with the correct filename and a binary
content type. Verify those actual response headers before activation. The
website links directly to the asset; it adds no executable-serving route,
proxy, GitHub credentials, student authentication or directory listing.

## Evidence required before activation

1. Identify final installer bytes and provenance: NJIT edition, source commit,
   version, exact filename, architecture, byte count and SHA-256 after signing,
   if applicable. Confirm parity with the intended online auditing functionality.
2. Pass native Windows installation, graphical launch without Python/developer
   tools, disconnected synthetic PDF audits, Help/Rules, reporting and exports,
   and safe graphical uninstallation. Test each advertised Windows version.
   Linux tests or simulated Windows calls do not satisfy this gate.
3. Resolve the concrete confidentiality conflict above and inspect the complete
   installer payload, including embedded archives. No private implementations,
   source, rule resources, dissertation data, credentials or repository history
   may be exposed. Do not substitute the generic edition to bypass this gate.
4. Publish only the qualified artifact to the separate public HTTPS endpoint.
   Download without credentials or cookies from an independent browser/network.
   Verify TLS and every redirect, attachment headers, actual installer format,
   exact size and SHA-256. Downloading a login/HTML page is a failure. Test the
   downloaded bytes on native Windows and retain evidence privately.
5. Review the implementation through the normal PR workflow. Deploy only the
   tested merged main SHA using [DEPLOYMENT.md](DEPLOYMENT.md). Check production
   `/version`, homepage, download, Help/Rules and a synthetic audit/report flow
   on desktop/mobile. The existing HTTP homepage does not substitute for HTTPS
   asset delivery or independent verification of the installer.

## Deployment configuration

All variables below use the prefix `NJIT_AUDITOR_WINDOWS_DOWNLOAD_`.
Every field is required to enable the link; absent/invalid fields fail closed.

| Suffix | Required value |
| --- | --- |
| `APPROVED` | `1` only after the complete release review |
| `EDITION` | `njit` |
| `NATIVE_TESTED` | `1` backed by the native qualification report |
| `CONFIDENTIALITY_REVIEWED` | `1` only after resolving the conflict and reviewing actual bytes |
| `URL` | Exact versioned HTTPS installer URL above |
| `SHA256` | 64 hexadecimal characters for the actual downloaded installer |
| `SIZE_BYTES` | Actual positive integer byte count |
| `ARCHITECTURE` | `x64` (other architectures require separate support) |
| `WINDOWS_VERSIONS` | `Windows 10`, `Windows 11`, or `Windows 10 and Windows 11`, as tested |

Version and release-notes URL derive from the installer URL. The card displays
supported Windows versions/architecture, version, exact bytes and MiB, normal
graphical installation instructions and an expandable SHA-256 checksum. No
terminal is required for student installation. Flags record operator decisions;
they do not verify remote availability or prove installer qualifications.

Set values together in the existing service's environment only after the gates
pass. Unset `APPROVED` or set it to `0` and restart that service to withdraw the
link. Preserve prior release metadata for rollback. Never edit the live checkout
or point it at a development branch. No production settings are enabled by this
commit.

## Validation scope

Run `tests/test_windows_download.py` with Playwright installed for release-gate,
template, keyboard and real Chromium layout checks at 320/390/1440 pixels. These
tests use synthetic release metadata with external networking blocked; they do
not claim an installer exists. Relevant existing synthetic web tests cover
uploads, audits, highlights, reports, Help/Rules and mobile parity. No native
Windows qualification, public artifact download or production deployment is
established by these Linux checks.
