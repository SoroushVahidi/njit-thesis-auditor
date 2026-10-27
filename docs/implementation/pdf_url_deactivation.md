# Temporary PDF URL auditing deactivation

Default web configuration hides the public-PDF-link form on every index
render, including upload/error/expired-job responses. POST `/audits/url`
returns HTTP 404 with guidance to upload a local PDF, before allocating a job,
creating a workspace, resolving a URL, or invoking the fetch implementation.
Help and About also hide URL-auditing instructions when the feature is disabled.
GET retains its existing harmless redirect to `/`. Local file uploads and
synthetic sample audits are unchanged. No deployed configuration was changed.

`src/njit_auditor/web_url_fetch.py`, the URL job route and its validation,
error handling and tests remain. Deliberate future **web** reactivation uses
`NJIT_AUDITOR_ENABLE_PDF_URL_AUDITING=1` in the server environment. Every other
value (including unset, `true`, or `yes`) is disabled. Request parameters and
form fields cannot enable it. The same predicate controls interface rendering
and POST acceptance. Desktop keeps excluding URL routes and the form regardless
of the flag, preserving its local-only architecture. A disabled desktop POST
can return 405 because the existing parameterized GET job route matches its
path; it never accepts URL work.

Reactivation is a separate reviewed deployment decision: first revisit existing
URL/SSRF/security limitations and upstream access restrictions. Changing the
flag does not fix them. Do not use it as a student or remote-request override.
Unit and browser tests cover the disabled default and local uploads. Existing
URL transport/UI regression tests now explicitly opt into reactivation; their
synthetic fixtures make no availability or network-policy claim.
