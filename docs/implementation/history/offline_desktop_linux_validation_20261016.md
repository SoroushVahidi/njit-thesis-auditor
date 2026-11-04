# Linux desktop validation — historical record, 2026-10-16

Extracted from the [desktop guide](../offline_desktop.md). The original validation
scope and dated candidate record below are preserved verbatim. They describe a
Linux development candidate before the [Windows rc.3 release](../../releases/windows-0.2.0-rc.3.md).
Statements about unfinished Windows work or distribution are historical, not the
current release status or new approval requirements. This is not native testing
of rc.3 or of the source changes merged after it.

## Validation scope

The native Linux one-folder build was exercised with a synthetic PDF: unauthorized requests were rejected, a local upload completed, report and highlighted PDF routes returned 200, and Quit left no listener or temporary audit files. A syscall trace showed only a bind to `127.0.0.1` and no non-loopback connects by the traced application. In-process tests completed an audit with outbound socket connects disabled. Linux network namespaces were unavailable on the workstation (`unshare -n`: operation not permitted), so a real disabled-network namespace test remains open. These checks do not certify confidentiality.

Online/offline parity tests use normal, Unicode, rotated, and low-text synthetic PDFs on the same source revision. They compare normalized JSON and Markdown, text reports, student-card data, PDF report text and drawings, original and highlighted PDF pages, and sorted/filterable HTML data. Job IDs, timestamps, and local file paths are the only normalized fields. Detector thresholds and rule IDs are unchanged.

**Platform status:** Linux x64 development build validated. Windows x64 spec and build instructions prepared; the Windows executable, installer experience, antivirus behavior, and native Windows launch/storage behavior remain untested until a Windows build and review. Do not distribute this candidate to Ester yet.

## Candidate validation record (2026-10-16)

The portable code at `7f6b165` passed Ruff (exit 0), mypy on 149 source files (exit 0), and the full local suite (4,769 passed, 10 private-material skips, 3 warnings; exit 0). The focused offline/web/report suite passed 374 tests (exit 0). The Linux x64 one-folder executable was rebuilt from that code and its launcher SHA-256 is `849b7e5cd5910cf18aa1a86150df73b4837c590c6f284be2f4ffbe5195cc1a05`; the binary is only one part of the 132 MB folder. Independent review: **APPROVE** for portable implementation and Linux development build, with Windows untested. A real browser interaction pass for the filter controls and a native Windows build remain before end-user distribution.
