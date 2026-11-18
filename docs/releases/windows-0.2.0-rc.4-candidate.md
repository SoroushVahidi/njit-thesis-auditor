# Windows beta 0.2.0-rc.4: local source candidate

This file records a local candidate, not a published installer or release.
The latest public beta is `desktop-v0.2.0-rc.3`, built from private source
`b83c7c81cf4043a17eb45f7b4b2042e55bbe947a`. Its published installer
must remain immutable. Incrementing the prerelease counter to `rc.4` creates
a distinct version and Windows file version `(0, 2, 0, 4)` for the next build.

The candidate starts from merged main
`35ed4e01cf09cab9fafeb179a5cecaa71c0d736b`. Build from the **final clean
committed source SHA** after reviewing this local preparation. The build script
embeds that SHA in `desktop-build-info.json`, and the metadata script records
it beside the resulting installer. Do not substitute the website SHA for a
later version-preparation commit. F08/P088, PR #661 analytics, and PR #656's
unmerged desktop export supervision are outside this candidate.

## Intended beta changes since rc.3

- Shared P018 page-number ownership and wrapped-folio recovery (#666).
- Appendix heading depth and TOC capitalization correction, and List of
  Figures/body-reference context correction (#665).
- Already merged Stage 1 and Stage 2 audit and student-facing improvements.
- Existing offline PDF audit, Help/Rules, JSON, Markdown, text, student PDF,
  highlighted PDF and combined PDF export flows remain supported.

The installed rc.3 executable cannot acquire these changes from the website.
Source parity tests are evidence for this candidate only; they do not qualify
an installer that has not been built. Esther's eight exact P018 examples remain
unverified without her original PDF or equivalent page extraction.

## Build and qualification gate

Use a clean committed checkout of the exact candidate SHA on native Windows
x64 with Python 3.12 x64, Windows PowerShell 5.1, Inno Setup 6, and the pinned
constraints in `packaging/offline-build-constraints.txt`. The existing builder
refuses a dirty checkout or non-Windows host.

```powershell
git status --short
git rev-parse HEAD
python -m pip install -c packaging/offline-build-constraints.txt -e ".[dev]" playwright pywinauto psutil
python -m playwright install chromium
python -m pytest -q tests/test_windows_startup.py tests/test_windows_install_harness.py tests/test_desktop_sessions.py tests/test_desktop_network.py tests/test_offline_desktop.py tests/test_desktop_parity_checkout.py tests/test_export_newlines.py tests/test_ester_r018_folio_baselines_20261117.py tests/test_ester_r018_wrapped_leader_folio_20261117.py tests/test_ester_r024_r055_20261117.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_offline_windows.ps1
python scripts/smoke_windows_beta.py --executable "dist/NJIT Thesis Auditor/NJIT Thesis Auditor.exe" --output .runtime/windows-validation/packaged-smoke
Get-FileHash "dist/installers/NJIT-Thesis-Auditor-Setup-0.2.0-rc.4.exe" -Algorithm SHA256
```

Require all hosted CI checks on the final source, the native startup/network,
locking and concurrent-export regressions, packaged synthetic audit and export
smoke, and the separate native Windows 11 checklist in
`docs/implementation/offline_desktop_windows_smoke.md`. Validate launch,
file selection, PDF parsing, all report/export formats, highlighting, offline
network isolation, error handling, file locks, temporary cleanup, installer
install/reopen/uninstall and version display. A Linux-skipped byte-range-locking
test is not a native pass. Hosted Windows Server is useful evidence, but it
does not establish clean Windows 11 installation qualification.

Inspect the bundle for private documents, credentials, logs and unexpected
network dependencies. Verify the generated EXE begins with `MZ`; independently
check its size and SHA-256 against the `.json` and `SHA256SUMS.txt` files.
The expected local output is the versioned installer plus those two metadata
files. Keep source, Git history, private fixtures and audit outputs out of the
public distribution repository.

PR #656 changes desktop export supervision and cache publication but is open
and has no hosted or native Windows pass on current main. Decide its scope
through a separate integration review before treating rc.4 as release-ready.
Do not merge it implicitly into this candidate. PR #640 is an older rc.2
development branch; current main contains the later rc.3 integration.

No Windows build or publication occurred in this preparation. Publication
requires separate authorization, actual installer bytes and metadata, release
notes that state observed Windows qualification limits, and an anonymous
postpublication checksum check. Do not overwrite rc.3.
