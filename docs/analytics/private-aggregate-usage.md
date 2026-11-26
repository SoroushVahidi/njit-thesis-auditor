# Private aggregate usage analytics

This optional web collector reuses the aggregate store and bounded writer from
PR #661. It includes the interrupted-producer repair. It summarizes events by UTC
day and uses no per-event database rows. It is disabled by default and separate
from the application database.

## Counter definitions

| Counter family | Boundary |
| --- | --- |
| Page views | Successful final HTML response to a GET on the home, help, about, or rules page. Excludes identified prefetch requests. A page view is not a person, browser, account, or session. |
| Submission attempts | The upload or approved sample handler begins. Framework or proxy rejections before the handler and retired shortcut routes are outside the count. |
| Accepted submissions | The application successfully schedules the PDF audit. Resubmissions count as new attempts. |
| Completed and failed audits | The in-process execution reaches one terminal outcome. Success requires initial report and view creation and the final application update. Failures include handled and unexpected audit errors. An unobserved terminal event cannot be inferred from an unmatched submission. |
| Report responses | Final successful ASGI response for one of Complete, Focused, Comments, JSON, Markdown, text, or legacy highlighted output. HTTP 200 and 206 are separate counters. Original PDFs are outside the classification. These are server responses and can include retries and ranges. |

The submission and audit families have two explicitly sourced subsets. A sample
started by the approved sample route contributes to `approved_sample`. A sample
uploaded as a PDF contributes to `upload`. Total counts include both subsets and
any events with unknown provenance. An `internal_` counter is a subset of its
corresponding total and uses only a trusted in-process operator or synthetic
context. Other activity is unclassified. No request header, forwarded address,
cookie, user agent, or identity awards that context.

Analytics events contain only a recognized date, bounded event category, optional
source/response class, internal flag, and coarse duration bucket. The collector
cannot retain documents, filenames, paths, finding or job identifiers, account
identifiers, or client addresses. It adds no browser session tracking, HTTP
statistics routes, or desktop telemetry.

The UTC day is assigned at collector admission. If work with a prior-day
timestamp is still queued or in a registered producer at midnight, that day's
coverage remains partial even if the batch later commits.
If a delayed observation changes an already observed UTC day, such as after a
backward host clock step, the count update and the coverage downgrade commit
together. An affected observed monthly rollup also becomes partial.

## Owner-only reporting and validation

The local report command opens an existing mode-0600 database in its mode-0700
owner directory, validates the exact aggregate schema, and queries it in a
read-only transaction:

```sh
PYTHONPATH=src python scripts/query_usage_aggregates.py \
  --db /absolute/private/usage.sqlite3 \
  --start 2030-01-01 --end 2030-02-01 --grouping weekly
```

Grouping supports daily, Monday-start weekly, monthly, and custom ranges. Bounds
are UTC dates, inclusive at the start and exclusive at the end. The result
includes exact totals only for fully observed periods. Partial periods expose
observed counts separately and unavailable periods retain null counts. Whole
observed monthly rollups and surviving day rows never overlap in a sum. Health
and storage interruptions degrade coverage. Previous database definitions are
not automatically migrated or mixed into the new definition.

Synthetic tests use private temporary SQLite files and injected collectors.
Requests never wait on database writes. Pending work has time and size bounds,
and retried writer batches are idempotent. Report and audit functionality remain
available while analytics is disabled or the collector is unavailable.

Production activation, private provisioning, retention, storage quotas and
access policy require separate authorization. The existing retention code's
90-day daily and 24-month monthly policies are engineering defaults for review.
This change provides no production provisioning or automatic scheduler.
See [Windows installer counter snapshots](installer-download-snapshots.md)
for the independent read-only metadata collection procedure.
