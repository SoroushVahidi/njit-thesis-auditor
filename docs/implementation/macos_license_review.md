# macOS dependencies and checking-rule disclosure review

This records technical evidence and questions for formal review, **not legal
advice, a licensing conclusion, or permission to distribute**. No vendor was
contacted, license purchased, source published or repository made public.

The macOS adaptation adds **macholib 1.16.4 (MIT)** to the build constraints.
It is PyInstaller's macOS Mach-O analysis dependency, not an application
framework. [Release metadata](https://pypi.org/pypi/macholib/1.16.4/json)
identifies its license. Existing altgraph is MIT; PyInstaller is
GPL-2.0-or-later with a bootloader distribution exception. The exception
concerns the PyInstaller bundle and does not remove other libraries' terms.

Tcl/Tk was already optional in the launcher; Mac builds now require a usable
non-system Tcl/Tk and bundle the selected runtime. Tcl/Tk uses a BSD-style
license, as stated by its [project](https://www.tcl-lang.org/software/tcltk/index.html).
The exact selected versions and notice bytes are recorded separately in
`NATIVE-RUNTIME-NOTICES.json`, `tcl-LICENSE.txt`, and `tk-LICENSE.txt`.
PyInstaller supplies runtime/framework collection; the supplemental collector
fails when notices cannot be located. The Python runtime has PSF and embedded
third-party notices collected from the build installation. Cocoa/system
frameworks are OS dependencies; the app does not add PyObjC/Electron/Qt.
The existing Pillow dependency converts the existing icon to ICNS at build
time. No generated image service or new icon library is used.

Existing bundled dependencies include PyMuPDF/MuPDF (AGPLv3 or Artifex
commercial terms), PDFium/pypdfium2 (BSD/Apache plus native third-party
notices), pdfplumber (MIT), pdfminer.six (MIT), pypdf (BSD), Pillow (MIT-CMU),
ReportLab (BSD), cryptography (Apache-2.0 OR BSD-3-Clause), lxml (BSD plus
native library notices), FastAPI/Starlette/Uvicorn (MIT/BSD family), Jinja2
(BSD), and the DejaVu font (its bundled font notice). The existing collector
copies installed distributions' license metadata/notices, including nested
PDFium notices. `DEPENDENCIES.json` and the dependency freeze are inspection
aids; the **actual Mac dylibs/frameworks**, bundled notices and native
subdependencies must still be reviewed. No actual Mac inventory exists yet.

[PyMuPDF 1.28.2 metadata](https://pypi.org/pypi/PyMuPDF/1.28.2/json)
declares dual AGPL/commercial licensing. The vendor's
[licensing page](https://pymupdf.io/licensing) describes reciprocal source
obligations and an alternative commercial arrangement. No applicable
commercial agreement or approved AGPL compliance plan was established here.
The project's MIT label alone cannot resolve these bundled-library duties.
Before conveying a private-test binary to another person, the authorized
reviewer must also decide whether that conveyance needs a compliance package;
"private testing" is not an assumed copyleft exemption.

## What the checking rules expose

Publishing the source would expose the included checking implementations.
The current package includes imported `njit_auditor.rules` modules, the
`pdf_audit` pipeline and supporting detection/report/student-correction code,
compiled into recoverable Python bytecode. It also explicitly includes
`data/processed/rules/project_added_rules.json` and
`data/specs/ester_warning_wording_map.json`, plus About/rule-reference
presentation. These contain rule IDs, descriptions, thresholds/conditions,
classification and wording logic sufficient to reveal substantial checking
behavior. This change does not modify those definitions or classifications.
Canonical/raw guideline files, dissertations, private ledgers, repository
history and private sample data are not intended bundle resources.

The PyInstaller spec does **not** provide encryption or rule secrecy. A
recipient can inspect data and recover bytecode. A private GitHub repository
restricts that repository's access, not the inspectability or license
obligations of a conveyed app. Therefore Professor Ziavras should be told
explicitly: **source publication exposes checking-rule implementations; a
packaged desktop app also exposes substantial rule logic and data. Do not
promise that NJIT's implemented rules remain private.**

If the AGPL applies to the combined application, the potentially required
Corresponding Source includes the covered application/library sources,
modifications, detector implementations and rule definitions needed to build
and run it, and relevant build/install scripts and interface definitions.
Review whether report/UI assets, fonts, linked native libraries and other
non-system dependencies belong in that package under their own terms. It is
not safe to assume that only changes to PyMuPDF need disclosure.
The [AGPL text](https://www.gnu.org/licenses/agpl-3.0.de.html) sections 1, 5,
6 and 13 and [GNU's FAQ](https://www.gnu.org/licenses/gpl-faq.en.html)
describe Corresponding Source, conveying binaries and network interaction.
The precise combined-work scope and obligations need authorized counsel.
Making source available to entitled recipients is distinct from making a
GitHub repository public; recipients' redistribution rights must also be
considered. Moving rules to separate Python modules/configuration does not
establish an exception and is not attempted here.

Formal review must resolve:

1. Who owns the application, implemented checking rules and guideline-derived
   content, and who may authorize their disclosure/redistribution?
2. Is there an applicable commercial PyMuPDF/MuPDF agreement, or an approved
   AGPL licensing/compliance route for the combined work and private-test
   conveyances? Are the existing hosted use and outputs also covered?
3. What exact Corresponding Source, notices, source delivery and installation
   information must accompany the chosen distribution route? Does any
   generated-PDF metadata/producer-notice obligation apply?
4. Are all native Mac dependencies and notice versions accounted for, with
   license-compatible terms and any font/PDFium/MuPDF obligations satisfied?
5. Who approves Developer ID use, notarization uploads, private test access,
   student distribution and any later source publication?

Until those decisions and native qualification are recorded, neither the
technical candidate nor its optional DMG is approved for student/public
release. Do not contact vendors or publish source/artifacts through this task.
