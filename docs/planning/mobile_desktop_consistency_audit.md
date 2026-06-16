# Mobile/Desktop Consistency Audit

## Scope

Routes checked:

- `/`
- `POST /audits`
- `/audits/{job_id}`
- `/audits/{job_id}/problems/category/{category}`
- `/audits/{job_id}/problems/rule/{rule_id}`
- `/audits/{job_id}/pdf`
- `/audits/{job_id}/pdf#page=N`
- `/audits/{job_id}/pdf/highlighted?...`
- `/help`
- `/rules`

Representative viewport profiles used in automated parity tests:

- Mobile profile: iPhone-sized request profile representing `390x844`
- Desktop profile: laptop-sized request profile representing `1440x900`

Test method:

- FastAPI `TestClient` rendering the same synthetic PDF audit job through both profiles
- Static template/CSS scan for risky responsive hiding patterns
- Direct requests to every rendered `/pdf` link on result and problem pages

Limitation:

- `TestClient` verifies server-rendered HTML, route behavior, link safety, and response headers.
- It does **not** execute a real browser layout engine, so it cannot prove CSS layout parity such as stacking, wrapping, or viewport overflow. Manual browser QA is still recommended for final presentation confidence.

## Differences Found

1. Result-page summary cards did not surface the substantive warning/error-style counts the user needs to compare across devices.

2. Grouped result cards exposed page navigation only as compact page-number links, while problem pages exposed explicit PDF action buttons. The action set was technically present but not presented consistently.

3. Problem-group example cards did not consistently show the same issue-type label surfaced on the main result page.

4. Existing responsive CSS did not show a mobile-only/desktop-only content fork, but this needed regression coverage because the parity risk was template/CSS drift rather than detector behavior.

## Differences Fixed

1. Result-page summary cards now show:
   - `Problems found`
   - `Needs fixing`
   - `Worth checking`
   - `Pages affected`
   - `Rules flagged`

2. Grouped result cards now include explicit PDF actions:
   - `Open highlighted PDF page` when highlight coordinates exist
   - `Open PDF page` when only page-level navigation exists
   - `Open PDF` when no page token exists

3. Grouped result cards now show an explicit `Issue type:` line.

4. Problem-group example cards now show an explicit `Issue type:` line, keeping the surfaced metadata aligned with the main result page.

5. Added regression tests covering mobile/desktop parity for:
   - home page content
   - upload redirect behavior
   - pending and failed job pages
   - completed result page content
   - category and rule problem pages
   - rendered PDF-link safety and inline-serving behavior
   - responsive hiding-pattern regression scan
   - help/rules PDF-only wording parity

## Intentional Responsive Differences Retained

These differences are layout-only and intentionally retained:

- stacked vs. wrapped button rows
- stacked vs. multi-column cards/grids
- section-header wrapping on narrow screens
- filter-bar wrapping on narrow screens
- rule-filter form stacking on narrow screens

No mobile-only or desktop-only substantive content branch was retained.

## Not Fully Fixable Here

1. True browser-layout parity was not validated with Playwright in this change.
   Reason:
   - the substantive risk in this repo is server-rendered content/action drift and PDF-route/header behavior, which is covered well with `TestClient`
   - adding Playwright would increase toolchain weight without improving coverage of the already-single-DOM templates as much as route/content assertions do

2. Browser-specific PDF viewer UX is still partly outside the app’s control.
   Reason:
   - the app now consistently serves PDFs with inline `Content-Disposition`
   - whether a browser embeds, previews, or downloads anyway can still depend on browser/device settings and installed viewers

## Remaining Risks

1. CSS-only overflow or wrapping problems could still affect presentation polish on specific browsers/devices even though content and actions remain present.

2. Client-side JS interactions such as grouped/individual toggling and filter behavior are covered structurally, but not with a full browser automation pass.

3. Any future template change that introduces mobile-only/desktop-only markup or responsive `display:none` on critical classes could reintroduce parity issues; the new regression scan is intended to catch that early.

## Validation

Validation commands and exact results are recorded after the final repo validation pass:

- `python -m pip install -e ".[dev]"` — passed
- `ruff check .` — passed (`All checks passed!`)
- `mypy src` — passed (`Success: no issues found in 91 source files`)
- `python -m pytest` — passed (`1325 passed, 1 warning in 8.93s`)

Final automated test count:

- `1325`
