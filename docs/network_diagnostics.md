# Network Diagnostics for Intermittent Browser Timeouts

This document describes a safe server-side diagnostic setup for the live NJIT Thesis Auditor
listener at `http://10.196.93.210:8000/`.

The web app itself is not changed by this setup. It adds a separate, root-managed metadata
capture for TCP traffic to the existing Uvicorn port so we can answer whether a client attempt
reached the server, whether the server replied, whether the TCP handshake completed, and whether
Uvicorn logged an HTTP request.

## Repository Evidence

Current checked-out deployment docs still describe the older tmux command:

- `docs/status/live_deployment_checklist.md`: `python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000`
- `docs/status/live_deployment_checklist.md`: manual URL `http://10.196.93.210:8000/`

Repository history contains the newer deployment model:

- live service: user-level `thesis-auditor-web.service`
- live worktree: `/home/soroush/njit-thesis-auditor/njit-thesis-auditor-clean-worktrees/live-current-main`
- host-specific unit: `~/.config/systemd/user/thesis-auditor-web.service`
- Uvicorn still runs with `--host 0.0.0.0 --port 8000`

The diagnostic service below is independent of the auditor service and should not require
restarting the auditor.

## What Gets Captured

The tcpdump wrapper records decoded TCP header lines only for traffic matching:

```text
tcp port 8000 and host 10.196.93.210
```

Optionally set `CLIENT_FILTER=10.196.115.152` to limit the capture to Esther's current failed-state
IPv4 address.

The log includes:

- timestamp
- source IP and port
- destination IP and port
- TCP flags such as `[S]`, `[S.]`, `[.]`, `[P.]`, `[R]`, `[F.]`
- TCP payload length as a number, when tcpdump prints it

The log does not include:

- packet payload/body bytes
- PDF uploads
- thesis text
- HTTP request or response bodies
- pcap files

The capture uses `-s 96` and writes tcpdump's text output, not raw packet files.

## Files Added

- `scripts/run_tcp8000_metadata_capture.sh` — tcpdump wrapper used by systemd.
- `scripts/inspect_tcp8000_diagnostics.py` — summarizes TCP events and optional Uvicorn access logs.
- `deploy/default/njit-thesis-auditor-tcp8000-diagnostics` — environment template.
- `deploy/systemd/njit-thesis-auditor-tcp8000-diagnostics.service` — system service template.
- `deploy/logrotate/njit-thesis-auditor-tcp8000-diagnostics` — log rotation template.

## Install and Start

Root privileges are required because tcpdump needs packet-capture permissions and the setup writes
under `/etc` and `/var/log`.

After this commit is present in the live deploy worktree, install the templates:

```bash
cd /home/soroush/njit-thesis-auditor/njit-thesis-auditor-clean-worktrees/live-current-main

sudo install -m 0644 deploy/default/njit-thesis-auditor-tcp8000-diagnostics \
  /etc/default/njit-thesis-auditor-tcp8000-diagnostics
sudo install -m 0644 deploy/systemd/njit-thesis-auditor-tcp8000-diagnostics.service \
  /etc/systemd/system/njit-thesis-auditor-tcp8000-diagnostics.service
sudo install -m 0644 deploy/logrotate/njit-thesis-auditor-tcp8000-diagnostics \
  /etc/logrotate.d/njit-thesis-auditor-tcp8000-diagnostics
```

For Esther-only capture, edit `/etc/default/njit-thesis-auditor-tcp8000-diagnostics`:

```bash
sudoedit /etc/default/njit-thesis-auditor-tcp8000-diagnostics
```

Set:

```text
CLIENT_FILTER=10.196.115.152
```

Then start the diagnostic service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now njit-thesis-auditor-tcp8000-diagnostics.service
sudo systemctl status njit-thesis-auditor-tcp8000-diagnostics.service --no-pager
```

This does not stop or restart `thesis-auditor-web.service`.

## Logs and Retention

TCP metadata log:

```text
/var/log/njit-thesis-auditor/tcp-8000.log
```

Rotation policy:

- daily rotation
- keep 14 rotated logs
- rotate early at 50 MB
- compress rotated logs
- `copytruncate` so the capture service can keep running

To test the logrotate rule without rotating:

```bash
sudo logrotate -d /etc/logrotate.d/njit-thesis-auditor-tcp8000-diagnostics
```

## Uvicorn Access Logs

The documented Uvicorn commands do not pass `--no-access-log`, so Uvicorn access logging should be
enabled by default. Under the current user-level systemd deployment, inspect it with:

```bash
journalctl --user -u thesis-auditor-web.service --since "2026-07-20 13:00:00" --no-pager
```

Under the older tmux fallback, access logs may also be in:

```text
.runtime/uvicorn-8000.log
```

No app code change is required to confirm this.

## Inspect Esther's Attempts

Use the helper from the deploy worktree:

```bash
cd /home/soroush/njit-thesis-auditor/njit-thesis-auditor-clean-worktrees/live-current-main
python scripts/inspect_tcp8000_diagnostics.py \
  --client-ip 10.196.115.152 \
  --since "2026-07-20 13:00:00" \
  --until "2026-07-20 13:15:00" \
  --show-lines
```

If Uvicorn logs are in a file instead of user journald:

```bash
python scripts/inspect_tcp8000_diagnostics.py \
  --client-ip 10.196.115.152 \
  --since "2026-07-20 13:00:00" \
  --until "2026-07-20 13:15:00" \
  --app-log .runtime/uvicorn-8000.log \
  --journal-unit "" \
  --show-lines
```

Direct grep is also useful:

```bash
sudo grep '10.196.115.152' /var/log/njit-thesis-auditor/tcp-8000.log
journalctl --user -u thesis-auditor-web.service --since "2026-07-20 13:00:00" --no-pager \
  | grep '10.196.115.152'
```

## How to Interpret Results

No SYN seen:

- The connection attempt did not reach the server's capture point.
- Most likely client-path, Wi-Fi/AP, VLAN, ARP/on-link, NAC, routing, or upstream firewall issue.
- Confirm Esther's timestamp, IP address, and that the diagnostic service was running.

SYN seen, no SYN-ACK:

- The server saw Esther's packet but no reply was captured.
- Check server firewall, local route selection, interface state, and whether Uvicorn is listening.
- Also check `ss -ltnp | grep ':8000'`.

SYN and SYN-ACK seen, no client ACK:

- The server replied, but Esther's laptop did not complete the handshake.
- This points to asymmetric path, client-side firewall/security software, AP/VLAN return-path issue,
  or dropped SYN-ACKs on the way back.

Full handshake but no HTTP request:

- TCP completed, but Uvicorn did not log an HTTP request.
- Possibilities: browser/proxy abort after connect, TLS attempted against plain HTTP, local security
  software interruption, or logging lookup issue. Check whether tcpdump shows client payload packets.

HTTP request reaches Uvicorn/FastAPI:

- The network path and TCP handshake worked.
- If the browser still reports a timeout, focus on browser/proxy behavior, response delivery, large
  response/PDF route behavior, or client-side handling.

## Rollback / Disable

Stop and disable capture:

```bash
sudo systemctl disable --now njit-thesis-auditor-tcp8000-diagnostics.service
sudo rm -f /etc/systemd/system/njit-thesis-auditor-tcp8000-diagnostics.service
sudo rm -f /etc/default/njit-thesis-auditor-tcp8000-diagnostics
sudo rm -f /etc/logrotate.d/njit-thesis-auditor-tcp8000-diagnostics
sudo systemctl daemon-reload
```

Optionally remove captured logs:

```bash
sudo rm -f /var/log/njit-thesis-auditor/tcp-8000.log*
sudo rmdir --ignore-fail-on-non-empty /var/log/njit-thesis-auditor
```
