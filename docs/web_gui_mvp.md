# Web Upload UI — MVP Guide

The NJIT Thesis Auditor includes a FastAPI web application that lets users upload a PDF
dissertation and receive a formatted audit report in the browser — no CLI or Python knowledge required.

---

## Running locally

```bash
python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000
```

Or use the helper script (works from any directory):

```bash
./scripts/run_web_gui.sh              # host=0.0.0.0, port=8000
./scripts/run_web_gui.sh 127.0.0.1   # localhost only
./scripts/run_web_gui.sh 0.0.0.0 8001  # alternate port
```

Then open `http://localhost:8000` in a browser.

---

## Persistent server (always-on via tmux)

### Start

```bash
tmux new -d -s thesis-auditor-web \
  'cd /home/soroush/njit-thesis-auditor && ./scripts/run_web_gui.sh'
```

### Check logs / output

```bash
tmux capture-pane -t thesis-auditor-web -p -S -200
tmux attach -t thesis-auditor-web   # attach (Ctrl-B D to detach)
```

### Restart

```bash
tmux kill-session -t thesis-auditor-web 2>/dev/null || true
tmux new -d -s thesis-auditor-web \
  'cd /home/soroush/njit-thesis-auditor && ./scripts/run_web_gui.sh'
```

### Stop

```bash
tmux kill-session -t thesis-auditor-web
```

### Verify it is running

```bash
tmux ls                                   # list sessions
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/   # should print 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/
```

---

## Access URLs

| Context | URL |
|---|---|
| Browser on same machine | `http://localhost:8000` |
| Browser on same machine | `http://127.0.0.1:8000` |
| Browser on LAN (if server IP is `10.x.x.x`) | `http://<server-lan-ip>:8000` |
| Public internet (requires reverse proxy + TLS) | `https://<domain>/` |

To find the server's LAN IP:

```bash
hostname -I
```

The server must be started with `--host 0.0.0.0` (default in `scripts/run_web_gui.sh`)
for LAN access. `--host 127.0.0.1` restricts to localhost only.

---

## Firewall notes

The helper script does not modify firewall rules. If your server runs UFW or firewalld and
port 8000 is blocked, ask your admin or run one of:

```bash
# UFW
sudo ufw allow 8000/tcp comment "NJIT Auditor web UI"

# firewalld
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

For production, prefer exposing only port 443 via a reverse proxy (see below) and keeping
port 8000 firewall-restricted to localhost.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NJIT_AUDITOR_WEB_RUNTIME_DIR` | `.runtime/web_audits` | Directory where uploaded PDFs and reports are written. Must be gitignored. |
| `NJIT_AUDITOR_WEB_MAX_UPLOAD_MB` | `50` | Maximum upload file size in MB. |
| `NJIT_AUDITOR_WEB_HOST` | `0.0.0.0` | Bind host for `scripts/run_web_gui.sh`. |
| `NJIT_AUDITOR_WEB_PORT` | `8000` | Bind port for `scripts/run_web_gui.sh`. |

---

## API routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Upload form |
| `POST` | `/audits` | Accept PDF upload; validate; start background audit; redirect to job page |
| `GET` | `/audits/{job_id}` | Job status page; auto-refreshes while running; shows findings when complete |
| `GET` | `/audits/{job_id}/status` | JSON polling endpoint (`state`, `finding_count`, timestamps) |
| `GET` | `/audits/{job_id}/download/json` | Download structured JSON report |
| `GET` | `/audits/{job_id}/download/markdown` | Download Markdown report |

---

## UX flow

1. User opens `/` and selects a PDF.
2. User clicks **Audit PDF**.
3. Server validates the file (extension, magic bytes, size limit) and starts a background job.
4. User is redirected to `/audits/{job_id}`, which polls every 2 seconds.
5. When complete, the page shows:
   - finding count by severity
   - grouped summary table (rules with 5+ findings)
   - full findings table (rule, page, severity, issue type, message)
   - copyable Markdown preview
   - download links for JSON and Markdown reports
6. If the audit fails, a clean error message is shown — no stack traces.

---

## Privacy and safety

- Uploaded PDFs are saved only under the runtime directory (gitignored).
- Generated JSON/Markdown reports are saved only under the runtime directory.
- No uploaded content is committed to the repository.
- Findings contain structural metadata only (page numbers, rule IDs, coordinates) — no
  dissertation body text, author names, or other private content.
- Runtime files are never committed: `.runtime/` is in `.gitignore`.
- Do not expose the web app to the public internet without a reverse proxy and TLS.

---

## Runtime storage

Each job creates a directory under `NJIT_AUDITOR_WEB_RUNTIME_DIR`:

```
.runtime/web_audits/
  {job_id}/
    upload.pdf     ← original uploaded file
    report.json    ← structured JSON audit report
    report.md      ← Markdown audit report
```

Job state is held in memory while the server runs. Restarting the server clears in-memory
state; existing on-disk reports remain accessible if you re-implement persistence.

---

## Reverse proxy (nginx/Caddy) — optional

For public or team access with TLS, run uvicorn on localhost and proxy from a public port.

**nginx snippet:**

```nginx
server {
    listen 443 ssl;
    server_name auditor.example.com;
    ssl_certificate     /etc/letsencrypt/live/auditor.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/auditor.example.com/privkey.pem;

    client_max_body_size 60M;   # must exceed NJIT_AUDITOR_WEB_MAX_UPLOAD_MB

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

**Caddy snippet (`Caddyfile`):**

```
auditor.example.com {
    reverse_proxy localhost:8000 {
        transport http {
            read_buffer_size 60MB
        }
    }
}
```

When using a reverse proxy, bind uvicorn to localhost only:

```bash
tmux new -d -s thesis-auditor-web \
  'cd /home/soroush/njit-thesis-auditor && \
   python -m uvicorn njit_auditor.web_app:app --host 127.0.0.1 --port 8000'
```

---

## Running tests

```bash
python -m pytest tests/test_web_app.py -v
```

Tests use `fastapi.testclient.TestClient` with monkeypatching of the audit runner;
no real PDF audit is needed for the web route tests.
