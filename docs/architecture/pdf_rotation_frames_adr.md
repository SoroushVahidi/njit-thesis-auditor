# ADR: PDF Rotation Frames and Rule Semantics

- **Status:** Accepted (design only). No behaviour change in this commit.
- **Date:** 2026-10-07
- **Applies from:** `655485a` (PR #579)
- **Scope:** every PDF detector rule, the highlight layer and the student PDF report.

## Context

A PDF page has a `/Rotate` attribute that tells the viewer to turn the sheet. It does not change the content stream. PyMuPDF reports the page's geometry in two different spaces:

- text, image and drawing boxes, and annotation rects (`add_rect_annot`, `annot.rect`), in the **unrotated, CropBox-relative** space;
- `page.rect`, and therefore `PdfPage.width` / `PdfPage.height` / `is_visually_landscape`, in the **displayed** space after `/Rotate`.

Rules that mixed the two were wrong on pages with a non-zero `/Rotate`. Four fixes since 2026-10-06 each adopted a locally justified convention:

| component | convention adopted |
|---|---|
| R011 (`pdf_margins.MarginFrame`, #572) | frame built from the unrotated size (`text_space_size`); landscape binding edge from the portrait folio's writing direction |
| P013/P019 (`detect_page_number_candidates`, #577) | candidates classified against unrotated bounds |
| Presentation (`pdf_highlight.PageBoxSpace`, #578) | clip in box space; generic location labels and markers in the displayed frame |
| R035 (`pdf_figure_table_layout`, #579) | measure in a *reading frame* (`reading_frame_rotation`); boxes mapped back to box space |

The read-only whole-page `/Rotate` audit on 2026-10-07 (266 synthetic cases) found that R035 is correct whenever the content turns with the page. It also confirmed two latent bugs:

- **B1.** On a viewer-only `/Rotate 90/270` page, R035 correctly keeps frame 0 but still uses the displayed width, height and landscape flag against unrotated boxes. The result is a wrong text-area centre and swapped 18/50 pt thresholds. A centred portrait figure becomes a 90 pt finding, and a 62 pt drift reads as 28 pt.
- **B2.** `reading_frame_rotation` is a character-weighted majority vote. On a near-tie it can be flipped by object-rotated text that happens to be upright in raw space.

No page in the 2,217 locally available thesis pages has a non-zero `/Rotate`. All of this is latent.

The open question is what a rule should do when `/Rotate` turns the displayed sheet but the authored content was not laid out in a correspondingly turned frame. B1 and the deferred R011 whole-page work both depend on the answer. Without one shared answer, every further fix would invent its own convention.

## Definitions

| term | meaning |
|---|---|
| **EXTRACTION_SPACE / BOX_SPACE** | Unrotated, CropBox-relative coordinates, origin (0, 0) even with a CropBox offset. All `PdfPage` boxes are stored here, and PyMuPDF annotations are drawn here. Size: `text_space_size(page)`. |
| **DISPLAY_FRAME** | The page as a viewer shows it after `/Rotate` (`page.rect`, `PdfPage.width/height`). Box → display: `box * page.rotation_matrix` (pure form: `pdf_highlight.box_to_display_space`). |
| **READING_FRAME** | The frame in which the page's authored content reads upright, given by a rotation R ∈ {0, 90, 180, 270} applied to box space. R is never inferred to be anything other than 0 or the page's own `/Rotate`. |
| **READING_FRAME_ROTATION** | R, inferred by `pdf_models.reading_frame_rotation` from line writing directions weighted by character count. It is an inference, not a fact (see *Confidence*). |
| **POLICY_FRAME** | The frame in which a formatting rule's decision is made. Under this ADR it is the reading frame. |
| **POLICY_ORIENTATION** | Portrait or landscape thesis page: the aspect of the reading frame (`width > 1.02 × height` ⇒ landscape). It does not come from `page.rect` and does not come from the raw `/Rotate` value. |
| **PAGE_ROTATION** | The numeric `/Rotate` value. |
| **OBJECT_ROTATION** | Content drawn rotated inside the page (a sideways table, vertical axis labels, a rotated caption) with no page `/Rotate` involved. |
| **VIEWER_ONLY_ROTATION** | `/Rotate` ≠ 0 while the content already reads upright in box space (R = 0). Only the viewer turns the sheet. |
| **CONTENT_TURNED_ROTATION** | `/Rotate` ≠ 0 with content stored so that it reads upright only after the viewer's turn (R = `/Rotate`). The page *displays* upright. |
| **PDFLSCAPE_STYLE_PAGE** | A content-turned page with a portrait MediaBox and `/Rotate 90` or `270`, whose reading frame is landscape. This is what LaTeX `pdflscape` writes. The physical portrait sheet is the box space. |
| **INTRINSIC_LANDSCAPE** | A landscape MediaBox with `/Rotate 0` (R = 0), e.g. Anthony's 38 landscape pages. |

**Operational test for viewer-only vs content-turned.**
- **Viewer-only:** the dominant body text has writing direction (1, 0) in box space, and `/Rotate` ≠ 0. Example: a portrait page saved with `page.set_rotation(90)`, which displays sideways.
- **Content-turned:** the dominant text reads (1, 0) only after mapping its direction through `/Rotate`. Examples: a pdflscape page (box-space direction (0, −1) at `/Rotate 90`), or an upright scan stored upside down with `/Rotate 180`.

## Decision

1. **Canonical geometry.** Box space stays canonical. Extraction is not normalized, and every stored box remains unrotated and CropBox-relative.
2. **Detector decisions follow the reading frame.** A rule evaluates layout in the reading frame. It maps boxes in with the page's rotation when R ≠ 0, and maps reported boxes back to box space. The frame's width, height and policy orientation come from the reading frame, never from `PdfPage.width/height` unless R equals the page rotation.
3. **Viewer-only `/Rotate` does not change detector decisions:** VIEWER_ONLY_POLICY_FOLLOWS_READING_FRAME. With R = 0, a viewer-only page is judged exactly like the same content with `/Rotate 0`:
   - same portrait/landscape policy and thresholds;
   - same margins and binding edge;
   - same centring and caption sides;
   - same page-number positions.
4. **Content-turned `/Rotate` (including pdflscape) is judged as displayed.** With R = `/Rotate`, the reading frame equals the displayed frame. A pdflscape page has a landscape reading frame, so landscape policy applies exactly as on the equivalent intrinsic-landscape page. Its physical-sheet semantics (binding edge, portrait page-number position) are derived from the portrait folio direction, as R011 already does for intrinsic landscape. They are never derived from the `/Rotate` value.
5. **Presentation follows the display.** Highlights are clipped and drawn in box space, because PyMuPDF annotations live there. Student-facing *generic* visual labels and markers are computed in the displayed frame, because they describe what the student sees on screen. Rule-specific semantic wording (e.g. R011's binding-margin label) comes from the rule's reading-frame decision and takes precedence.
6. **Global extraction normalization is rejected:** GLOBAL_EXTRACTION_NORMALIZATION_REJECTED.
   - PyMuPDF's unrotated extraction is stable.
   - Same-space geometry fixed P013/P019 (#577) without rewriting extraction.
   - Presentation already maps explicitly to the display (#578).
   - R035's rule-level reading frame (#579) handled every content-turned family tested.
   - `Page.remove_rotation()`, or an equivalent blanket rewrite of extracted coordinates into the displayed frame, would erase the distinction between viewer-only and content-turned pages: viewer-only content would become sideways. That contradicts decision 3 and R011's pinned test, and it would force presentation to map back for annotations.

   This rejects *blanket* normalization only. Narrow, explicit coordinate transforms inside a rule or presentation component (box ↔ reading frame, box → display) remain the intended mechanism.
7. **Ambiguous reading frames are not guessed.** See the next section.

### Confidence (B2) and ambiguous pages

`reading_frame_rotation` is an **inference**, not authoritative policy. Future code should distinguish a **confident** frame from an **ambiguous** one:

- **Confident:** the winning orientation clearly dominates. For example, it carries most of the page's characters and wins by a material margin rather than by a few characters.
- **Ambiguous:**
  - a near-tie between "upright as displayed" and "upright in box space" (B2: 320 vs 319 characters);
  - no text;
  - only a folio.

Behaviour on an ambiguous frame:

- **`/Rotate 0` pages are never ambiguous.** R = 0 by definition, and object rotation is a separate matter.
- **On a `/Rotate` ≠ 0 page with an ambiguous frame, rotation-sensitive rules abstain.** This covers centring, caption side, margin side, page-number position, and anything else that depends on axis or orientation. Silent abstention is preferred to a confident wrong frame, and a tie must never become a confident orientation.
- **Rules that are not rotation-sensitive are unaffected,** for example text-content rules.
- **Current behaviour (legacy, not the target):** today's helper returns 0 on ties and when there is no text. It can also pick a non-zero frame from a lone folio that reads upright only after `/Rotate`. These are **not** confident determinations; they are simply the existing fallback. The fallback is tolerated until a confidence signal exists, because no real page is affected and R035 needs a caption, which makes no-text and folio-only pages inert for R035. Future code must represent the ambiguous state explicitly rather than treat a tie or an empty page as a confident frame 0.

The confidence threshold, and whether to add structural signals (folio direction, caption direction, image or drawing orientation), are follow-up engineering. This ADR does not set a numeric threshold.

## Why the reading frame and not the display

| evidence | supports |
|---|---|
| R011's `test_rotate_flag_does_not_change_the_verdict` (90/180/270) requires viewer-only `/Rotate` to leave R011's verdict, side and box unchanged | reading frame |
| Pixel-equivalent pdflscape and intrinsic-landscape pages must agree (P013/P019, R035, highlight differential tests); this holds only when content-turned pages are judged as displayed | reading frame (= display for content-turned pages) |
| Option A (display) makes a verdict depend on viewer metadata alone. On a viewer-only page the content is *sideways* in the display frame, so display-frame centring or margin measurement has no coherent meaning: B1's 90 / 152 pt drifts are exactly this mix | reading frame |
| The relevant authority is about the physical thesis page:<br>- page numbers keep their portrait (letter-format) position on landscape sheets (NJIT guideline; Ester's R035 verdict on Anthony p60; Ester's comments on the Aguado DOCX draft);<br>- margins apply through the entire document (NJIT guideline);<br>- Aguado's landscape sections keep a 1.5 in top/bottom binding margin (observed layout, not a comment);<br>- landscape-aware R035 tolerance (Ester's Anthony verdicts).<br>All of it concerns the authored page, not a viewer's turn. Sources are the private review ledger, the live review sheet and the EF-annotated drafts; none is tracked in this repository | reading frame (derived) |
| Direct Ester authority on `/Rotate` viewer metadata | **none exists**; not needed, because decision 3 is the engineering meaning of a viewer attribute, not a new formatting policy |

Authority classification:
- **DIRECT_ESTER_AUTHORITY:** landscape page-number position (Anthony p60, Aguado comments); landscape-aware R035 tolerance (Anthony).
- **Guideline text:** page numbers keep their portrait position on landscape pages; margins apply through the entire document.
- **Observed layout, not authority:** the 1.5 in landscape binding margin in Aguado.
- **ENGINEERING_INTERPRETATION_OF_PDF_ENCODING:** decisions 2–4. They are how a PDF viewer attribute maps onto that physical-page authority, checked against pixel-equivalent encodings.
- **ENGINEERING_CONVENTION:** decisions 1, 5, 6; confidence handling.
- **NO_AUTHORITY:** Ester has never addressed `/Rotate` metadata.

This ADR claims **no** Ester authority for:
- viewer-only `/Rotate`;
- reading-frame inference;
- the extraction-space architecture;
- rejecting `remove_rotation()`.

These are engineering conclusions; no question to Ester is required, and no reviewer policy changes.

## Consequences by rule

| rule / component | extraction space | decision frame (ADR) | policy orientation | display transform | current compliance | future work |
|---|---|---|---|---|---|---|
| R011 margins (`pdf_margins`) | box | reading frame; binding edge from folio direction | reading-frame aspect | none | **Already correct:** /Rotate 0 and viewer-only 90/180/270 (pinned test). **Largely correct:** pdflscape 90 decisions. Box space *is* the physical portrait sheet, and the 2026-10-07 differential (Anthony's pages re-encoded pdflscape-style) found identical decisions. **Not verified:** pdflscape 270, including the bottom-only allowances on a counter-clockwise sheet. **Pending:** pdflscape side *wording* (`left_margin` where intrinsic says `top_margin`, binding); content-turned portrait pages at 90/180/270 (box-space frame ≠ reading frame) | Build `MarginFrame` in the reading frame, then derive binding from folio direction as for intrinsic landscape |
| P013/P019 page numbers | box | reading frame; portrait folio position from the sheet | reading-frame aspect | none | Compliant for /Rotate 0 and pdflscape 90/270 (tested). Viewer-only is compliant by construction (box space = content frame) but has no dedicated test. **Not compliant** for content-turned 180, and current code does **not** implement this ADR's 180 answer: the displayed-bottom folio is classified `top_center` (pinned by `test_rotate_180_page_is_classified_in_text_space`) | Classify in the reading frame. The 180 question is answered by this ADR (displayed bottom ⇒ `bottom_center`); it is engineering, not policy |
| R035 figure/table layout | box (rules horizontal in the reading frame) | reading frame | reading-frame aspect (18 / 50 pt) | none | Compliant for every content-turned family; **B1** on viewer-only 90/270 | On R = 0, use `text_space_size` and a box-space landscape flag; add confidence gating (B2) |
| P082 landscape page-number orientation (experimental, off) | box | angle relative to the reading frame | reading-frame aspect | n/a | Adds raw `/Rotate` to line angles (`visual_angle`): display semantics, not compliant | Use R instead of the raw `/Rotate` when re-enabled |
| Other PDF detectors (14 rule files using `page.width/height`, excluding P082) | box | reading frame | reading-frame aspect | none | Rotation-naive: correct at /Rotate 0 only | Migrate rule by rule as each is touched |
| Generic highlight layer (`pdf_highlight`) | box | n/a (presentation) | n/a | yes: generic labels and overflow markers | Compliant (#578) | none |
| Student PDF report | box | n/a | n/a | yes: badges | Compliant (#578) | none |
| Legacy CLI `rules/page_numbers.py` | `page.rect` height | n/a (not in the web flow) | display | n/a | Not compliant; out of scope | Retire or migrate if revived |

### Rule semantics per page family (expected under this ADR)

| family | R | R011 binding / sides | R035 policy | P013 folio |
|---|---|---|---|---|
| Normal portrait | 0 | left 1.5 in; others 1 in | portrait 18 pt | bottom/top centre |
| Intrinsic landscape | 0 | binding top or bottom from folio direction; landscape wording | landscape 50 pt | portrait folio on the long edge |
| pdflscape 90 / 270 | 90 / 270 | as intrinsic landscape (same physical edges) | landscape 50 pt | as intrinsic landscape |
| Viewer-only 90 / 180 / 270 | 0 | identical to the unrotated page | identical to the unrotated page | identical to the unrotated page |
| Content-turned portrait 90 / 180 / 270 | /Rotate | as normal portrait, judged as displayed | portrait 18 pt | as normal portrait, judged as displayed (180: displayed bottom = `bottom_center`) |
| Ambiguous `/Rotate` ≠ 0 page | — | abstain from side-dependent findings | abstain | abstain from position findings |

## Test compatibility (at `655485a`)

| test | current expectation | ADR-compatible | why |
|---|---|---|---|
| `test_p011_landscape_margin_frame.py::test_rotate_flag_does_not_change_the_verdict` | viewer-only 90/180/270 equals plain | **YES** | this is decision 3 |
| `test_p013_p019_rotated_page_numbers.py`: pdflscape, intrinsic, pixel-equivalent P019 tests | pdflscape folio = bottom-centre in the portrait sheet; P019 agrees across encodings | **YES** | box space = physical sheet for pdflscape |
| `test_p013_p019_rotated_page_numbers.py::test_rotate_180_page_is_classified_in_text_space` | content-turned 180 folio → `top_center` | **NO** (interim) | It encodes pre-ADR text-space behaviour, and its own docstring defers the question. Under this ADR the displayed-bottom folio is `bottom_center`. The P019 outcome (no finding) is the same either way. Update it in the P013/P019 reading-frame follow-up. |
| `test_rules/test_r035_pdflscape_geometry.py` (intrinsic = 90 = 270 equivalence, rules, captions, highlight) | identical verdicts | **YES** | decision 4 |
| `test_r035_pdflscape_geometry.py::test_viewer_only_rotation_keeps_existing_measurement` | viewer-only finding *boxes* equal the control's | **YES, but weak** | It compares boxes only, so it passes despite B1's wrong drift and threshold. The B1 fix should strengthen it to compare drift and allowed delta. |
| `test_rotated_page_highlight_geometry.py` | clip in box space; labels, markers and badges in display | **YES** | decision 5 |

## Shared page-frame abstraction

**SHARED_FRAME_OBJECT_RECOMMENDED**, with deliberately limited scope. Today four components re-derive pieces of the same model (`text_space_size`, `PageBoxSpace`, `box_to_display_space`, `reading_frame_rotation`, R035's `_reading_frame_page`). Detector rules should converge on one object built from a `PdfPage`, holding only:

- `box_size` (= `text_space_size`)
- `page_rotation`
- `reading_rotation` and `reading_confident`
- `reading_size` and `policy_orientation`
- `to_reading(bbox)` and `from_reading(bbox)`

Display-frame mapping stays in the presentation layer (`PageBoxSpace`), which is built from stored sizes in the web flow and has no `PdfPage`. This is not over-general. Every field except `reading_confident` already has a consumer, and `reading_confident` is required by decision 7. The object is a recommendation only; nothing in this ADR implements it. The object should be introduced alongside the first follow-up fix that needs it (R035 B1), not as a standalone refactor.

## Rejected alternatives

- **Policy always follows the display.** It makes verdicts depend on viewer metadata, breaks R011's viewer-only test, and on viewer-only pages measures sideways content in a frame where centring and margins are meaningless (B1).
- **Policy follows the raw `/Rotate` value.** It cannot tell viewer-only from content-turned pages, which share the same `/Rotate`. For example, it would turn a viewer-only portrait page into a landscape page. B1 is exactly this failure: R035's landscape flag follows the displayed, `/Rotate`-swapped size.
- **Global `remove_rotation()` / extraction normalization.** Rejected in decision 6.
- **Independent rule-specific ad-hoc width/height swapping.** This produced the current four conventions. R011's swap is correct only because box space happens to be the physical sheet on pdflscape pages, and it is wrong for content-turned portrait pages.

## Consequences

**Positive**
- One direction for R035 B1: on R = 0 the frame is box space, with box-space size and orientation.
- One direction for R011 whole-page `/Rotate` and for P013/P019 at 180.
- `PdfPage.width/height` is reserved for display concerns.
- A clear split between detector geometry (reading frame) and presentation geometry (box space plus display).

**Costs and risks**
- Reading-frame inference can be ambiguous (B2) and needs a confidence signal.
- 14 rule files (plus P082) still use displayed dimensions and must be migrated rule by rule. No migration has happened yet.
- Viewer-only and content-turned pages are latent today, with zero real-corpus impact. Each migration must be proven with pixel-equivalent differential tests and a zero corpus delta.

## Non-goals

This ADR does **not**:
- normalize extraction;
- fix R035 B1;
- fix R011 or P013/P019 whole-page behaviour;
- change any current finding, threshold or test;
- change reviewer policy or create reviewer authority;
- certify arbitrary object rotation (sideways tables, vertical captions on `/Rotate 0` pages).

## Migration guidance

For each rule touched:
1. Build the frame once per page.
2. Map every box, and the page size, into the reading frame.
3. Decide there.
4. Map reported boxes back to box space.
5. Never mix `PdfPage.width/height` with box coordinates.
6. Abstain on ambiguous frames for rotation-sensitive decisions.

Prove each migration with pixel-equivalent intrinsic / content-turned / viewer-only fixtures and a zero real-corpus delta.

## Follow-up work (ranked)

1. **R035 B1:** reading-frame size and orientation on R = 0, introducing the shared frame object. It is the only confirmed rule bug, and it is narrow.
   **Implemented:** `pdf_models.PdfReadingFrame` (box size, page rotation, reading rotation, reading-frame size, policy orientation, `to_reading`/`from_reading`). R035 is its only consumer and no longer reads `PdfPage.width/height/is_visually_landscape`; viewer-only `/Rotate` 90/180/270 now gives the `/Rotate 0` verdict whenever the reading frame is inferred as 0 (a B2 near-tie can still infer a non-zero frame). `reading_confident` is deliberately not added yet: the frame uses today's `reading_frame_rotation` unchanged, so B2 (item 4) is still open.
2. R011 whole-page `/Rotate` and pdflscape side wording.
   **Implemented:** R011 measures each page in its `PdfReadingFrame` (via `PdfReadingFrame.page_in_reading_frame`, now shared with R035) and stores finding boxes in box space. Sides, binding edge (still from the portrait folio's reading direction), policy orientation and the bottom-only allowances refer to the reading frame, so pdflscape 90/270 and content-turned portrait pages match their `/Rotate 0` controls, and viewer-only pages keep their verdict whenever the frame is inferred as 0. B2 is still open: a near-tie that flips the inferred frame now also changes R011's side naming.
3. P013/P019 content-turned 180 semantics (decided above; update the interim test).
4. B2 confidence signal and abstention.
5. P082 (re-enable only with reading-frame angles) and the legacy CLI.
