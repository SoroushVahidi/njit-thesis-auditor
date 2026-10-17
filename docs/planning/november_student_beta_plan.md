# Proposed November second-review student beta

This is an operational proposal for a limited, voluntary pilot after GSO and stakeholder review. It does not alter institutional requirements or promise acceptance.

## Entry gate

- Obtain explicit stakeholder review of the student cards and report against the October 15 feedback and the official self-assessment sheet. Confirm the documented LaTeX font exception is explained and resolve or label the List of Figures case conflict with GSO authority.
- Complete a synthetic end-to-end run on the intended host: supported and invalid upload, findings, filters, highlight navigation, download, and report reading at phone and desktop widths.
- Replay authorized false-positive and true-positive cases without changing thresholds or rule IDs. Investigate material regressions before inviting students.
- Establish the offline-app/Windows and anonymizer distribution status separately. Do not offer either as ready without its own validation and privacy review.

## Student instructions

1. Work from a copy of the dissertation and upload only through the approved deployment. Do not upload private material to a demo or unapproved host.
2. Read the result summary and “What was checked.” Start with red problems; use filter, page and highlighted-PDF links to locate evidence.
3. Check each warning against the official GSO sheet and current guidance. Correct the source document, regenerate the PDF, and run the audit again. A blank finding list is not a compliance certificate.
4. Download the combined PDF report for personal review. Fill out and submit the official self-assessment sheet separately as directed by GSO. Keep local copies secure.
5. Manually check the items listed in the report, particularly scanned/image content, committee details, equations, source settings, references, and optional acknowledgments.

## Support, feedback, and monitoring

Provide a named support owner, an approved contact channel, an expected response window, and a route for reporting false positives before enrollment. Collect only the minimal issue description and a synthetic or redacted reproduction when possible. Do not place dissertation text or reviewer comments in public issues, logs, or tracked reports. Track aggregate upload success, report-download success, incomplete checks, missing highlights, accessibility problems, and adjudicated false-positive/true-positive changes. Have a recovery path for expired jobs and failed downloads.

## Pause and expansion

Pause invitations if an upload/report path fails repeatedly, a critical finding navigates to the wrong page, private content appears in a public artifact, or a known adjudicated case regresses. Investigate and retest the exact final build. Expand only after a small cohort can complete the workflow, stakeholders accept the wording and report, the support owner can handle feedback, and the separate offline/anonymizer work has its own readiness evidence. Record decisions; a merged PR alone is not acceptance.
