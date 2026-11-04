# About Us: content provenance and desktop release status

The website and shared desktop source use `templates/about.html` at `/about`.
The base navigation includes the page on upload, status, results, Help and Rule
Reference pages. The desktop package allowlist includes the template; rendering
uses only bundled resources, with no automatic external requests.

## Verified public facts

| Fact | Basis |
| --- | --- |
| Soroush Vahidi: NJIT Computer Science PhD student and developer/maintainer | [NJIT-hosted profile](https://web.njit.edu/~sv96/), `pyproject.toml` authorship, and repository history. The profile uses the more specific “Ph.D. candidate”; “PhD student” is used on the page. |
| Ester Flaim: Assistant Director of Graduate Studies | [Current NJIT directory](https://people.njit.edu/profile/ef264). Her own project correspondence corroborates the spelling. The earlier terminology instruction to use “Esther” was incorrect and is corrected without renaming identifiers. |
| Ioannis Koutis: Professor of Computer Science; early project discussions | [Current NJIT directory](https://people.njit.edu/profile/ikoutis) verifies the title. Authorized project correspondence supports early discussions. The user clarified that he does not advise this project; no project supervision is claimed. |
| Sotirios G. Ziavras: Vice Provost for Graduate Studies and Dean of the Graduate Faculty | [NJIT directory](https://people.njit.edu/profile/ziavras) and [NJIT-hosted faculty page](https://web.njit.edu/~ziavras/). |
| Development began in May 2026 | Initial scaffold commit `c9164f2f80f5c54f8214d2e3cdde0224376dff43`, dated May 19, 2026. Early May 21 commits show source checks followed by PDF auditing. |
| Windows beta released in November 2026 | Published desktop release `desktop-v0.2.0-rc.3` and PR #644. |

Authorized project correspondence corroborates the workshop context, early
project discussions, initial formatting checklists, ongoing rule/usability
feedback, and feedback on preparing a student beta. Only these general public
facts are used. No message bodies, private links, student identities, document
titles, attachments, or private reports are included in the page or this document.

Acknowledgments describe individual input, not institutional endorsement or
software authorship by the acknowledged collaborators. The precise workshop date
and any additional unverified contribution roles are omitted. The page does not
claim funding, institutional approval, or shared ownership.

The public `njit-thesis-auditor-desktop` repository is labeled **downloads and
releases**, not the application's public source repository. Source remains private.

## Pending desktop installer

About Us (PR #646), the acknowledgment correction (PR #647), and the student wording improvements (PR #645) are implemented
in shared desktop source, **pending inclusion in the next installer release**.
No Windows build or rc.3 replacement is part of this task. The existing installer
remains version `0.2.0-rc.3`, 41,326,578 bytes, SHA-256:

`70713e44f18aaac32d5cc244aee3c82c7badbd8ce9d9dbf3b1dffe919a05f690`

A future installer must have its own version and checksum. External email and
release links require connectivity only when deliberately opened.

The [rc.3 release record](releases/windows-0.2.0-rc.3.md) distinguishes its native hosted evidence from subsequent Ubuntu source/browser checks.
