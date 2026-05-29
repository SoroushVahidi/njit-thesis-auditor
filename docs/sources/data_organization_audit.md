# Data Organization Audit

- Date: 2026-05-29
- Branch: organize-project-data-files

## Purpose

Documents the organization of newly added dissertation and guideline files,
large-file inventory, and Git LFS recommendations.

---

## Organization Changes Made

### Files Moved (git mv)

Three dissertation files were previously committed to the repository root.
They have been moved to `data/raw/ester/` for cleaner organization:

| Old Path (root) | New Path |
|-----------------|----------|
| `250218 Cibaku Elson First Review.pdf` | `data/raw/ester/250218 Cibaku Elson First Review.pdf` |
| `260415 Yin H _2nd_review with EF Comments.pdf` | `data/raw/ester/260415 Yin H _2nd_review with EF Comments.pdf` |
| `Dissertations with no Feedback -20260529T012213Z-3-001.zip` | `data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip` |

### Files Added

Handout / guideline files from the `ai-formatting-project.rar` archive added
to `data/raw/guidelines/`:

| File | Size | Category |
|------|------|----------|
| `Thesis and Dissertation Formatting Guidelines (WIP).docx` | 881 KB | Rule file |
| `Front Matter Pages Lorem Ipsum.pdf` | 280 KB | Example / template |
| `PhD Title Pages.pdf` | 157 KB | Example / template |
| `Self-Self Assessment Sheet.pdf` | 106 KB | Checklist |
| `Titles Examples Level 1 to 5.docx` | 21 KB | Rule / example |
| `Dissertation Review Process.pdf` | 224 KB | Process guide |
| `PhD Dissertation Process Roadmap .xlsx` | 14 KB | Process / admin |
| `Link to PQ ETD Administartor_.docx` | 7 KB | Admin reference |

---

## Current Repository File Layout (data/)

```
data/
  evaluation/
    generated/          ← gitignored (generated audit outputs)
    private/            ← gitignored (private evaluation artifacts)
  processed/
    examples/
      ester_feedback_examples.json
    rules/
      front_matter_rules.json
      njit_rule_inventory.json
      project_added_rules.json
  raw/
    ester/              ← EF-annotated dissertation data
      260330_YESNO_audit_logic_matrix.xlsx
      250218 Cibaku Elson First Review.pdf
      260415 Yin H _2nd_review with EF Comments.pdf
      Dissertations with no Feedback -20260529T012213Z-3-001.zip
      Yin_H_4th_Review_with_EF_comments_compressed.pdf
      Yin_Haotian_Second_R_with_EF_Feedback.pdf
    guidelines/         ← NJIT formatting rule/guideline files (new)
      Dissertation Review Process.pdf
      Front Matter Pages Lorem Ipsum.pdf
      Link to PQ ETD Administartor_.docx
      PhD Dissertation Process Roadmap .xlsx
      PhD Title Pages.pdf
      Self-Self Assessment Sheet.pdf
      Thesis and Dissertation Formatting Guidelines (WIP).docx
      Titles Examples Level 1 to 5.docx
```

---

## Large File Inventory

Files over 5 MB currently tracked in the repository:

| File | Size | Over 25 MB | Over 50 MB | Over 100 MB |
|------|------|:----------:|:----------:|:-----------:|
| `data/raw/ester/260415 Yin H _2nd_review with EF Comments.pdf` | ~16 MB | No | No | No |
| `data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf` | ~16 MB | No | No | No |
| `data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf` | ~2 MB | No | No | No |
| `data/raw/ester/250218 Cibaku Elson First Review.pdf` | ~5.5 MB | No | No | No |

No currently tracked files exceed 25 MB. Files in the original archive that
were NOT committed due to size (these remain in the local archive only):

| File (in archive, not committed) | Size |
|----------------------------------|------|
| `Yin H 3rd review with EF Comments.pdf` | 61 MB |
| `Yin H 4th review with EF comments.pdf` | 59 MB |
| `Aguado Alvaro 3rd Review...EF comments.docx` | 19 MB |
| `Termini_DoloresThirdReview with EF comments.pdf` | 16 MB |
| `Sebastian.Fine 3rd Review...EF comments.docx` | 11 MB |

---

## Git LFS Status

`.gitattributes` declares LFS attributes for binary files:

```
*.pdf filter=lfs diff=lfs merge=lfs -text
*.docx diff=lfs merge=lfs -text
*.xlsx diff=lfs merge=lfs -text
*.pptx diff=lfs merge=lfs -text
*.zip  diff=lfs merge=lfs -text
```

**Current status:** `git-lfs` is not installed on this machine. All binary files
are stored as regular git blobs. The LFS filter declarations are aspirational —
they will take effect once `git lfs install` is run and `git lfs migrate` is
used to convert existing large-file blobs.

**Recommendation:** Install Git LFS before adding any files over 25 MB to the
repository. For files already committed as blobs, use `git lfs migrate import`
to convert them retroactively (requires force-pushing, coordinate with
collaborators).

---

## Duplicate / Archive Observations

- The `ai-formatting-project.rar` source archive should not be committed (added
  to `.gitignore` with `*.rar`).
- The `Dissertations with no Feedback -20260529T012213Z-3-001.zip` is committed
  as a zip because it is small (312 KB) and contains a useful clean baseline PDF.
  Extracting and committing the PDF directly would also be acceptable.
- The `Yin_H_4th_Review_with_EF_comments_compressed.pdf` in `data/raw/ester/` is
  a compressed version of the larger `260430 Yin H 4th review...` file in the
  archive. Both can coexist — the compressed version is what is committed.

---

## Gitignore Changes

Added to `.gitignore`:
- `*.rar` — prevents accidentally committing archive bundles
- `/tmp/rar_extract/` and `/tmp/handouts/` — local extraction directories

---

## Cleanup Still Recommended Before PR?

The current organization is clean and functional. No further cleanup is required
before merging this branch. Optional future actions:

1. **Git LFS migration:** Convert committed PDFs to LFS pointers once `git-lfs`
   is installed. Not blocking.
2. **Large archive files:** The three large Yin review PDFs (59–61 MB each) in
   the original archive are not committed. If they become needed for evaluation,
   add them only after Git LFS is set up.
3. **Filename normalization:** Filenames with spaces and date prefixes like
   `250218 Cibaku Elson...` are functional but unconventional for scripting.
   Consider renaming to underscores in a future cleanup commit.
