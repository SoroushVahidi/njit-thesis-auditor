# Ester Materials: Source Files for the NJIT Thesis Auditor

These materials were shared by Ester Farfan (NJIT Graduate Studies formatting
coordinator) for use in this project. The project owner has confirmed that all
files in this archive are permitted for use within this repository.

Original bundle: `ai-formatting-project.rar` (196 MB, Google Drive)

---

## Rule / Guideline Files

Located in `data/raw/guidelines/`. These are the authoritative NJIT formatting
sources and should be used when encoding or verifying audit rules.

| File | Description | Key Rules Covered |
|------|-------------|-------------------|
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | Main NJIT formatting spec | Margins, fonts, page numbers, front matter structure, abstract |
| `Front Matter Pages Lorem Ipsum.pdf` | 13-page annotated mock front matter | Page layout, heading placement, front matter ordering |
| `PhD Title Pages.pdf` | Title page guide by department | Title page format, department-specific variations |
| `Self-Self Assessment Sheet.pdf` | 4-page GSO self-assessment checklist | Margins, font, line spacing, front matter section content |
| `Titles Examples Level 1 to 5.docx` | Heading level formatting guide | Level 1 = ALL CAPS bold centered; Level 2 = Title Case bold; Levels 3–5 also specified |
| `Dissertation Review Process.pdf` | 3-stage review process overview | Review workflow context (not a formatting rule) |
| `PhD Dissertation Process Roadmap .xlsx` | Timeline and action items checklist | Administrative milestones |
| `Link to PQ ETD Administartor_.docx` | ProQuest ETD submission link | ProQuest submission info (administrative) |

**Especially important for P020 (APA title case):** `Titles Examples Level 1 to 5.docx`
confirms that Level 2 headings use Title Case (each word capitalized except articles,
prepositions, and conjunctions).

---

## Commented / Reviewed Dissertation Data

Located in `data/raw/ester/`. These are real dissertation drafts annotated by
Ester Farfan. They are the primary evaluation dataset for measuring auditor
performance against human reviewer feedback.

Do not reproduce dissertation body text in documentation, reports, or tests.
Use only aggregate counts and high-level issue categories.

| File | Student | Review Round | Format |
|------|---------|-------------|--------|
| `250218 Cibaku Elson First Review.pdf` | Elson Cibaku | 1st | PDF |
| `260415 Yin H _2nd_review with EF Comments.pdf` | H. Yin | 2nd | PDF |
| `Yin_Haotian_Second_R_with_EF_Feedback.pdf` | H. Yin (Haotian) | 2nd (variant) | PDF |
| `Yin_H_4th_Review_with_EF_comments_compressed.pdf` | H. Yin | 4th (compressed) | PDF |
| `260330_YESNO_audit_logic_matrix.xlsx` | — | Rule matrix | XLSX |

Additional EF-annotated files available in the original archive (not fully committed
due to size — see data organization audit):

- `250128 Sebastian.Fine Revised 1st Dissertation Draft EF.pdf`
- `250129 Kang, Qi EF comments.pdf`
- `250204 Kang Qi PhD dissertation_1st review with EF comments.pdf`
- `250213 Pennock Andrew Revised 1st Dissertation Draft with EF comments.pdf`
- `250409 Sebastian.Fine 3rd Review Draft with EF comments.docx`
- `250415 Termini_DoloresThirdReview with EF comments.pdf`
- `250828 Aguado Alvaro 3rd Review Dissertation Draft with EF comments.docx`
- `260428 Yin H 3rd review with EF Comments.pdf`
- `260430 Yin H 4th review with EF comments.pdf`
- `260528Luo M 3rd review with EF comments.pdf`

Note: DOCX files likely contain tracked changes and embedded reviewer comments.
Files dated `26xxxx` are from 2026; files dated `25xxxx` are from 2025.

The `260330_YESNO_audit_logic_matrix.xlsx` is the source for extracted front-matter
compliance rules used in `data/processed/rules/`.

---

## Clean / No-Feedback Dissertation Data

Located in `data/raw/ester/`.

| File | Student | Status |
|------|---------|--------|
| `Dissertations with no Feedback -20260529T012213Z-3-001.zip` | Sebastian Fine | Zip containing clean draft (Revision 3, no EF annotations) |

Useful as a "before" baseline for comparison against annotated versions of the
same student's dissertation.

---

## Process / Admin References

Available in the original archive under `Presentations /` (not committed — large size):
- `First Review Workshop.pptx` — Workshop slides explaining the review process
- `Create a ProQuest Account Final.pptx` — Step-by-step ProQuest ETD guide

Extract locally from the archive if needed.

---

## Notes

- **Git LFS:** `.gitattributes` declares LFS attributes for `*.pdf`, `*.docx`, `*.xlsx`,
  `*.pptx`, and `*.zip`. However, `git-lfs` is not currently installed on this machine.
  Until LFS is installed, files are stored as regular git blobs. Install with
  `git lfs install` once available if repo size becomes a concern.
- **Permissions:** The project owner has confirmed all materials in this archive are
  permitted for use in this private repository.
- **Privacy:** Files contain real student names. The repo is currently private.
  Do not make it public without first reviewing student data handling.
- **Body text:** Avoid committing or reproducing full dissertation body text in
  documentation, test fixtures, or evaluation reports.
