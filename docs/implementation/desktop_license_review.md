# Desktop dependency and distribution review

This is a preparation record, not legal clearance or release approval.
The project MIT declaration does not replace the licenses of bundled libraries.

The pinned builder inventory identifies PyMuPDF 1.28.2 as “Dual Licensed - GNU
AFFERO GPL 3.0 or Artifex Commercial License”, with its COPYING notice present.
The vendor documents [AGPL and commercial licensing](https://pymupdf.io/licensing).
No commercial-license evidence or approved AGPL distribution plan was established
in the reviewed packaging/configuration documents. Keeping the repository private
is not, by itself, a licensing basis for distributing an inspectable binary.
Resolve the applicable terms with the authorized licensing decision-maker before
public distribution. This task does not buy a license, accept new terms, change
the project's license, or publish corresponding source.

The clean builder's inventory also records PyInstaller's GPLv2-or-later license
with its bootloader distribution exception, Pillow's MIT-CMU, cryptography's
Apache-2.0 OR BSD-3-Clause, ReportLab's BSD notice, and pypdfium2's BSD/Apache and
native dependency notices. The new build step collects installed distribution
license metadata, license/notice/COPYING files (including nested PDFium dependency
notices), and the builder's CPython notice into `third-party-licenses/`. The
DejaVu font and notice remain explicitly bundled. It excludes direct_url.json,
installation paths, credentials, and arbitrary project/source files.

This inventory is a review aid. It is not a proof of all native DLL obligations
on a Windows artifact that has not been built. Review the actual Windows bundle,
its dependency freeze, and its notices before approval. The proposed Windows
package must include the third-party notice directory and dependency manifest.
The release configuration additionally requires `licensing_reviewed=true` and
an approved `license_basis` (`commercial` or `agpl-compliant`), alongside existing
native test, public URL/checksum, and distribution approval gates. Defaults
remain false/empty. These fields record a human decision; they do not establish
that an agreement or compliance plan exists.

PyInstaller packages Python bytecode and assets rather than encrypting source.
They can be inspected or recovered. Do not bundle source secrets, private PDF
fixtures, ledgers, credentials, `.git`, or unrelated data. A private GitHub source
repository stays private, but its visibility setting cannot make distributed
application code secret. Existing allowlisted resources, bundle-name checks,
and archive inspection remain required; do not represent an inventory check as
an arbitrary-byte confidentiality proof.

For non-Store Windows distribution, choose an approved publisher/signing policy.
[Microsoft's reputation guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)
explains why signatures do not guarantee absence of SmartScreen warnings.
Defender/SmartScreen and signing were not tested here because Windows was
unavailable. Do not disable antivirus or enroll in paid signing services as part
of this task. Verify the ZIP's SHA-256 after any signing/repackaging; record the
final bytes and update the disabled candidate manifest before review.
