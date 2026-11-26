# Online Auditor deployment and rollback

This is the canonical release runbook. The approved restricted operational
appendix identifies the service, credentials, checkout, storage paths, and
authorized fixtures. Check the appendix with the responsible operator before
acting. Keep those details out of public documentation, issues, and job output.

## Before cutover

### Clean-worktree requirement

1. Obtain release authorization. Establish the exact remote main commit, tree,
   and seven successful exact-checkout hosted jobs. Record the current
   production revision and the exact rollback target before scheduling downtime.
2. Use the designated clean production checkout and service environment.
   Verify the candidate source and resolved dependencies independently of the
   development environment. Use LFS-free qualification for hosted jobs.
   The operator handles approved fixture provisioning separately.
3. Check public and loopback `/healthz` and `/version`. Confirm the service is
   in the intended role and its approved configuration remains in effect,
   including disabled production analytics and the intended reviewer and
   administrative access settings.
4. Check for active audit or export work. Follow the approved maintenance
   procedure, then make a fresh private SQLite backup. Verify its owner-only
   mode, checksum, and integrity. Record sanitized digests or counts for
   accounts, feedback, comments, attachments, and configuration. Confirm the
   rollback checkout and environment are available.

## Cutover verification

1. Switch only to the exact qualified revision and use the service supervisor
   for the restart. Verify the running source SHA and tree and confirm the
   exact version and health through public and loopback routes.
2. Run approved synthetic upload and download smoke checks. A successful audit
   must publish terminal metadata only when the required reports are available.
   Verify HTML, JSON, text, Markdown, and PDF reports, finding references, and
   highlight geometry. Check that failed audits conceal partial outputs and
   private details.
3. Verify the authorized reviewer workflow, General Feedback, and attachment
   behavior at their appropriate test scopes. Verify the database and effective
   configuration against the before snapshots and confirm analytics remains
   disabled. Run approved correction and retained-regression checks at the
   recorded synthetic, excerpt, or exact-original scope.
4. Record terminal receipts before updating deployment dispositions or
   communicating release completion. See
   [reproducibility](REPRODUCIBILITY.md) and [hosted CI privacy](CI_PRIVACY.md).

## Rollback

On a failed cutover gate, use the approved rollback procedure to restore the
previous verified code and environment. Preserve the live feedback database
and both sets of receipts. Restore database data only if necessary under the
approved backup and recovery decision. Recheck public and loopback health,
version, reviewer access, database integrity, row and attachment preservation,
and disabled analytics. Record the failed gate and restored revision.

## Maintenance handoff

The private appendix should record the responsible operator, exact service and
environment, approved access, the release lock, retention policy, backup
verification, rollback instructions, evidence location, and notification
authority. Use [reviewer and administrative feedback](implementation/admin_feedback.md)
for the feature contract and [the status snapshots](status/CURRENT_STATUS.md)
for dated source and production observations.
