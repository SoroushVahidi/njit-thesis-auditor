# Private Windows installer counter snapshots

Use this optional maintenance command with a separately approved owner-only
directory and database. It does no work during application startup and installs
no scheduler. The fetch operation reads only public GitHub release JSON at a
fixed HTTPS endpoint. It verifies the approved release and installer asset IDs,
version, name, size, and checksum where pinned. It sends no token, follows no
redirect, and downloads no installer.

Run from an authorized source checkout with an absolute database path in an
existing mode-0700 directory. Initialization creates a new mode-0600 file.

```bash
PYTHONPATH=src python scripts/snapshot_installer_downloads.py --db "$snapshot_db" init
PYTHONPATH=src python scripts/snapshot_installer_downloads.py --db "$snapshot_db" capture --slot 2026-11-27
PYTHONPATH=src python scripts/snapshot_installer_downloads.py --db "$snapshot_db" report --start 2026-11-27 --end 2026-11-30
```

Supply the intended UTC calendar date for the capture slot. The command saves the
actual UTC observation and reports the delay from the intended midnight. The
first result for an asset and slot is immutable, including an unavailable
result. Taking a new observation at a later slot preserves the missing coverage.
Each approved asset is reported separately. Confirm a replacement's identity
before adding it to the manifest. Mark previous entries inactive to preserve
their readable history without collecting further snapshots for them.

The first observed count is a baseline. Comparable consecutive daily
observations supply delta evidence over their actual interval. Missing slots,
withdrawals, decreasing counters, reordered observations and changed digests
break continuity. The report keeps the last observation and last successful
provider count with their timestamps. For a requested range, a count is exact
only as a counter difference with covered, matching endpoints. Other covered
ranges show bounds. A coverage gap leaves the upper bound unknown. A bound with
no supporting interval is also unknown.

The provider count measures observed installer download events. It cannot
identify an individual, actual installation, automated activity or repeated
download by a person. Activity attribution stays unclassified. The separate
store contains public release metadata and no web usage records.
