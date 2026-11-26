# Administrator finding feedback

This feature is off by default. Student audits and exports remain available without login. The
Windows offline app does not expose administrator routes or controls.

## Activation requirements

An operator must provision all four settings outside the repository and outside deployment
artifacts before activation:

- `NJIT_AUDITOR_ADMIN_ENABLED=1`
- `NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED=1`, only after verifying end-to-end HTTPS or an equivalent
  secure access mechanism
- `NJIT_AUDITOR_ADMIN_SESSION_KEY`: at least 32 random bytes encoded as URL-safe base64,
  provisioned through a restricted secret manager or environment file. Generate it in a private
  operator terminal with `python -c 'import secrets; print(secrets.token_urlsafe(32))'`.
- `NJIT_AUDITOR_ADMIN_DB_PATH`: absolute path ending in `.sqlite3` in a persistent directory
  owned by the service account and mode `0700`; for example, a private directory under
  `/var/lib/`, outside Git, deployment releases, and the audit runtime

The database file is created at mode `0600`. The service refuses a symlinked database, a
group/world-accessible parent directory, a path inside the repository or audit runtime, and an
unknown schema version. Operators should use a dedicated service account and restrict access to
the environment file and backups as well. Do not put passwords, the session key, or database in Git.

Provision the first individual account locally on the server, with the database path set and
administrator login still disabled, using `njit-admin create <username>`. The command prompts
twice for the password on a terminal; never pass it as a command argument. Usernames are
case-insensitive ASCII identifiers of 3–32 characters, starting with a letter and then containing
letters, digits, `.`, `_`, or `-`. The command optionally accepts `--display-name`. No account is
created automatically and there is no web registration or reset endpoint. Operators can use
`njit-admin list`, `njit-admin disable <username>`, `njit-admin enable <username>`, and
`njit-admin reset <username>`. Disablement and password reset revoke all sessions belonging to
that account. Keep a separate account for each reviewer.

The former `NJIT_AUDITOR_ADMIN_PASSWORD_HASH` setting is ignored. A version 3 upgrade revokes
all shared-password sessions; those reviewers must be provisioned individual accounts.

The application also checks the actual ASGI request scheme. Production must terminate TLS at a
trusted proxy and pass a verified HTTPS scheme to Uvicorn. Trust forwarded headers only from the
known proxy address; do not trust client-supplied `X-Forwarded-*` headers. The existing deployment
checklist shows Uvicorn bound to `0.0.0.0` without TLS. Before activation, make its upstream port
unreachable from untrusted clients, confirm the proxy replaces incoming forwarding headers, and
verify that a plain-HTTP request with forged `X-Forwarded-Proto` cannot reach the login form.
An ASGI app cannot independently prove the physical TLS state after a proxy rewrites its scheme.
If either the deployment verification flag or HTTPS scheme is absent, login and every feedback
endpoint fail closed. Do
not set the activation flags until TLS, proxy trust, private storage, and backups have been reviewed.

Administrator sessions are stored server-side in SQLite, expire after eight hours, and are
revoked on logout. Cookies are `Secure`, `HttpOnly`, `SameSite=Strict`, and host-only. All
administrator writes require a session CSRF token and an exact same-origin `Origin` header.
Failed logins are throttled in SQLite (five per client address and thirty globally in a
15-minute window). When multiple reviewers share one proxy address, the per-address limit applies
to them together.

## HTTP reviewer beta

The separate reviewer form is disabled unless
`NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED=1` is set. It works only on HTTP and does
not enable the HTTPS administrator login. It uses the same protected SQLite path and
session key described above, with an independent HTTP cookie and eight-hour session.
The operator must create only the two initial reviewer accounts locally with
`njit-admin create-reviewer soroush` and `njit-admin create-reviewer ester`; both
commands prompt for distinct passwords on a terminal. Reviewer accounts can submit
per-finding feedback but cannot sign in to administrator routes or edit or delete
feedback. The browser has no registration or password reset interface. Use passwords
unrelated to NJIT credentials. HTTP carries credentials and session cookies in clear
text, so enable this mode only for the explicitly accepted beta.

The operator can disable a reviewer with `njit-admin disable <username>`; this also
revokes that reviewer's sessions. The normal public audit flow requires no login.

## Schema and privacy

SQLite `PRAGMA user_version=5` is the explicit schema version. `feedback` has a random ID, random
audit/job reference, raw-index-based per-audit finding reference, rule ID, issue type, PDF page,
original confidence, one of four classifications, comment, workflow status, safe rule/issue
context, creation and update timestamps, and optional resolution timestamp. An index on the audit
and finding references supports multiple independent reviews of one finding. Status choices are Open,
In Progress, and Resolved. New reviews record the submitting account ID. Edits record the
last modifying administrator ID; resolution records the resolving administrator ID. Reopening
clears the active resolution identity and timestamp. Confirmed deletion removes the review and
retains a limited tombstone with the deleting administrator ID and finding reference. Legacy
reviews remain unattributed rather than being assigned an invented identity. The `admins` table
stores stable random account IDs, unique canonical usernames, Argon2id password hashes, account
role, status, creation timestamps, and optional display names. `sessions` stores only keyed token
hashes, account IDs, and expiration times;
CSRF tokens are derived per request and are never stored in the database. `login_attempts`
stores short-lived pseudonymous throttling buckets. Uploaded PDFs, raw extracted text, file paths,
and student report exports are not written to this database. Reviewers should avoid entering
personal or confidential dissertation text in free-text comments.

The normal audit retention sweeper only removes the audit workspace. Saved feedback remains after
expiration, but no new feedback can be submitted for a missing or expired audit. Feedback never
changes audit rules, confidence, severity, or generated reports. Resolved feedback is retained
until an administrator explicitly deletes it.

## Backup, restore, and migration

Back up the database with SQLite's online backup API or the `sqlite3` CLI
`.backup` command. Store the backup with owner-only access. Check it with
`PRAGMA integrity_check` and record `PRAGMA user_version`. Keep the session key
in a separate protected backup. Rotating it will invalidate existing sessions.

If restoration is necessary, disable administrator login and stop the service
before restoring to the configured database path. Set the parent directory to
`0700` and the database to `0600`. Revoke restored sessions before startup.
Verify the schema, account IDs, reviewer attribution, feedback rows, and
attachment digests. Audit files are stored separately.

The current schema is version 5. The application migrates versions 1 through 4
transactionally and preserves feedback IDs and records. Use a version 5
compatible application to restore a version 5 backup. See the
[deployment runbook](../DEPLOYMENT.md) for production checks and code rollback.
