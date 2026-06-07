# Web Upload UI — MVP Guide

The NJIT Thesis Auditor includes a FastAPI web application that lets users upload a
dissertation **PDF**, **TeX source (.tex)**, or **LaTeX project ZIP**, paste a public PDF URL,
or audit a built-in sample PDF, and receive a formatted audit report in the browser — no CLI
or Python knowledge required.

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
| `NJIT_AUDITOR_WEB_RUNTIME_DIR` | `.runtime/web_audits` | Directory where uploaded files and reports are written. Must be gitignored. |
| `NJIT_AUDITOR_WEB_MAX_UPLOAD_MB` | `50` | Maximum upload file size in MB. |
| `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` | `86400` (24 h) | How long completed/failed jobs remain in memory and on disk before automatic cleanup. Invalid or non-positive values fall back to the default. |
| `NJIT_AUDITOR_WEB_HOST` | `0.0.0.0` | Bind host for `scripts/run_web_gui.sh`. |
| `NJIT_AUDITOR_WEB_PORT` | `8000` | Bind port for `scripts/run_web_gui.sh`. |

---

## API routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Upload form + URL input form + built-in sample form |
| `POST` | `/audits` | Accept PDF, TeX, or ZIP upload; validate; start background audit; redirect to job page |
| `POST` | `/audits/url` | Accept public PDF URL; download safely; start background audit; redirect to job page |
| `POST` | `/audits/sample` | Accept built-in sample ID; copy local sample; start background audit; redirect to job page |
| `GET` | `/audits/{job_id}` | Job status page; auto-refreshes while running; shows findings when complete |
| `GET` | `/audits/{job_id}/status` | JSON polling endpoint (`state`, `finding_count`, timestamps) |
| `GET` | `/audits/{job_id}/download/json` | Download structured JSON report |
| `GET` | `/audits/{job_id}/download/markdown` | Download Markdown report |

---

## UX flow

### File upload (PDF, TeX, or ZIP)

1. User opens `/` and selects a **PDF**, **.tex**, or **.zip** file.
2. User clicks **Start audit**.
3. Server validates the file (extension, magic bytes, size limit) and starts a background job.
4. **PDF** uploads run layout rules **P011–P061**. **TeX** and **ZIP** uploads run source rules
   **P001–P010** (ZIP is safely extracted, main `.tex` is detected — **no LaTeX compilation**).
5. User is redirected to `/audits/{job_id}`, which polls every 2 seconds.
6. When complete, the page shows findings, JSON/Markdown download links, and a Markdown preview.
7. If the audit fails, a clean error message is shown — no stack traces.

### Public PDF URL

1. User opens `/` and pastes a public direct PDF URL into the URL form.
2. User clicks **Audit PDF URL**.
3. Server validates scheme (`http`/`https` only), resolves the hostname, and rejects private/internal addresses.
4. Server downloads the PDF into the runtime job directory (streamed; size-limited).
5. Server validates that the downloaded bytes start with `%PDF`.
6. Same background audit and results flow as file upload.

### Built-in repository sample PDF

1. User opens `/` and selects a sample from the dropdown.
2. User clicks **Audit Sample**.
3. Server looks up the sample ID in the curated registry (`src/njit_auditor/web_samples.py`).
4. Server validates the local file (path stays under repo root; file exists; magic bytes are `%PDF`).
5. Server copies the sample into the runtime job directory.
6. Same background audit and results flow as file upload.

**Privacy note:** Built-in samples are local repository evaluation files. They are available only
on servers where the repository is checked out. Do not expose the built-in sample feature on a
public site unless you are authorized to process those files.

### URL safety restrictions

- Only `http://` and `https://` schemes are accepted.
- `localhost`, `127.x.x.x`, `10.x.x.x`, `172.16–31.x.x`, `192.168.x.x`, `169.254.x.x`, IPv6 loopback/private/link-local are blocked.
- Hostnames are resolved before download; any address mapping to a private range is rejected.
- Redirects are checked at each hop — no redirect may target a private address.
- Download timeout: 15 seconds.
- Size limit: same `NJIT_AUDITOR_WEB_MAX_UPLOAD_MB` as file uploads.
- ZIP files are not supported for URL audit (only direct PDF links work).

---

## Privacy and safety

- Uploaded PDFs/TeX/ZIP files, URL-downloaded PDFs, and built-in sample copies are saved only
  under the runtime directory (gitignored).
- Generated JSON/Markdown reports are saved only under the runtime directory.
- Web-generated JSON/Markdown exports use **basename-only** paths (no absolute server paths in
  metadata or source `details.file`). The HTML findings table shows polished comments only.
- No uploaded, downloaded, or sample content is committed to the repository.
- Findings contain structural metadata only (page numbers, rule IDs, coordinates, basename:line
  for source) — no dissertation body text, author names, or other private content in the default UI.
- Runtime files are never committed: `.runtime/` is in `.gitignore`.
- URL downloads are SSRF-safe: private/internal IP ranges and `localhost` are blocked server-side.
- Built-in sample IDs are a fixed curated list; arbitrary file paths cannot be submitted via the form.
- **Public hosting:** the default bind is `0.0.0.0`. Do not expose the web app to the public
  internet without a reverse proxy, TLS, authentication, and rate limiting.
- Do not expose built-in samples on a public site unless you are authorized to process those files.

---

## Runtime storage and job TTL

Each job creates a directory under `NJIT_AUDITOR_WEB_RUNTIME_DIR`:

```
.runtime/web_audits/
  {job_id}/
    upload.pdf     ← PDF upload, URL download, or built-in sample copy
    upload.tex     ← TeX upload
    upload.zip     ← ZIP upload (extracted under the same job dir)
    report.json    ← structured JSON audit report
    report.md      ← Markdown audit report
```

Job state is held in memory while the server runs. **Automatic cleanup** removes completed and
failed jobs (and their directories) after `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` (default 24 hours).
Cleanup runs on server startup, before new jobs are created, and when job pages are rendered.
Jobs still `pending` or `running` are never removed early. Restarting the server clears
in-memory state; on-disk files remain until TTL cleanup or manual deletion.

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
