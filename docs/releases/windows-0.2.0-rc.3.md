# Windows beta 0.2.0-rc.3 — immutable release record

This is the published Windows installer, not the current website/shared-source
revision. Keep source in the private `SoroushVahidi/njit-thesis-auditor` repository.
The [public desktop repository](https://github.com/SoroushVahidi/njit-thesis-auditor-desktop)
is for **downloads/releases**, not the application's public source.

| Field | Verified value |
|---|---|
| Version | `0.2.0-rc.3` |
| Filename | `NJIT-Thesis-Auditor-Setup-0.2.0-rc.3.exe` |
| Size | **41,326,578 bytes** |
| SHA-256 | `70713e44f18aaac32d5cc244aee3c82c7badbd8ce9d9dbf3b1dffe919a05f690` |
| Exact build source | `b83c7c81cf4043a17eb45f7b4b2042e55bbe947a` |
| Private annotated source pin | `source/desktop-v0.2.0-rc.3` at that exact source commit |
| Successful hosted build | [41756930261](https://github.com/SoroushVahidi/njit-thesis-auditor/actions/runs/41756930261), head SHA equals the build source |
| Source integration | PR #644 squash merge `2bde1eac57324dfc2692eca5cb3b79e8875eb4d5`; exact source and merge trees match |
| Target / build host | Windows 11 x64 target; hosted `windows-2025` / Windows Server build host |

Public locations:

- [Release and beta notes](https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/tag/desktop-v0.2.0-rc.3)
- [Installer](https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/download/desktop-v0.2.0-rc.3/NJIT-Thesis-Auditor-Setup-0.2.0-rc.3.exe)
- [Machine-readable byte metadata](https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/download/desktop-v0.2.0-rc.3/release-metadata.json)
- [SHA256SUMS](https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/download/desktop-v0.2.0-rc.3/SHA256SUMS.txt)

The public `desktop-v0.2.0-rc.3` tag belongs to the separate distribution repository;
it does **not** pin private source. The annotated `source/desktop-v0.2.0-rc.3` tag
belongs only to the private source repository. Verify with:

```bash
git cat-file -t refs/tags/source/desktop-v0.2.0-rc.3
git rev-parse 'refs/tags/source/desktop-v0.2.0-rc.3^{}'
git ls-remote origin refs/tags/source/desktop-v0.2.0-rc.3 'refs/tags/source/desktop-v0.2.0-rc.3^{}'
```

Do not move existing tags or overwrite published bytes. Keep the original source
release branch/worktree and private qualification evidence as additional provenance.
Do not upload that source/evidence, credentials, student PDFs or audit outputs.

## Completed checks and limits

Successful hosted Windows Server checks: **63 native startup/network/concurrent-export
tests**, **472 focused regressions**, and packaged startup, synthetic audit, exports,
local Help/Rule Reference, readable completion time and shutdown smoke. Installer
publication was followed by a fresh anonymous live-button download with matching
size/checksum and a PE executable response. Metadata and build-run provenance were
rechecked from Ubuntu on 2026-11-04.

These results do not establish clean Windows 11 qualification, installer/uninstaller
lifecycle, antivirus behavior or every manual native check. Those remain unperformed;
see the [native checklist](../implementation/offline_desktop_windows_smoke.md).
Ubuntu source-template, simulated frozen-bundle and browser tests are separate
source evidence, not additional native tests of this executable.

## Later Linux check of the frozen source

Creating the private source pin triggered the historical commit's ordinary Ubuntu
workflow: [run 41771678101](https://github.com/SoroushVahidi/njit-thesis-auditor/actions/runs/41771678101).
With the dependencies installed by that run, Python 3.10 reported 8 failures and
3.11/3.12 reported 9 each. Assertions covered older wording/navigation expectations,
validation-error redirects, and (3.11/3.12) a synthetic R035 image-geometry fixture.
The corresponding tests were changed after rc.3; the frozen source's full Linux
suite is not claimed green. This is separate evidence from its completed hosted
Windows Server regressions and packaged smoke. The exact pin and published installer
remain unchanged; no historical tests or checks were weakened for this record.

## Changes after rc.3

PR #645's [student wording/checklist changes](../STUDENT_WORDING_USABILITY.md),
PR #646's About Us/navigation and PR #647's [acknowledgment correction](../ABOUT_US_CONTENT.md)
are in the website/shared source and **await the next installer**. Website deployment
does not alter rc.3. A future Windows build needs a new version/checksum and its own
validation record. No new Windows build or asset mutation is part of repository organization.

See [publication/build procedure](../PUBLIC_WINDOWS_RELEASE.md) and
[installation/source development](../implementation/offline_desktop.md).

## Upload-only source update (2026-11-04)

The shared desktop source now requires uploaded PDFs for audits. The synthetic
example is a download that users save and upload manually. URL audit shortcuts
are disabled in the website and shared source. This source change does not
replace the published rc.3 executable. No Windows rebuild or publication is part
of this task; the published installer remains 41,326,578 bytes with SHA-256
`70713e44f18aaac32d5cc244aee3c82c7badbd8ce9d9dbf3b1dffe919a05f690`.
