"""Synthetic recovery and opt-in immutable-baseline/production acceptance evidence."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from test_analytics_collector import manual_collector
from test_analytics_schema import FakeClock
from test_analytics_store import apply
from test_analytics_store import database as database
from test_analytics_web import snapshot_audit
from test_analytics_web import web as web

from njit_auditor.analytics.collector import BoundedCollector
from njit_auditor.analytics.runtime import AnalyticsRuntime
from njit_auditor.analytics.schema import PageView
from njit_auditor.analytics.store import AggregateStore

BASELINE = "148599ccd516da534edab652f5f0da33d53f42f6"
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "readonly",
        "full",
        "corrupt",
        "transaction",
        "overflow",
        "blocked",
        "terminated",
        "locked",
        "clock",
    ],
)
@pytest.mark.parametrize("audit_fails", [False, True])
def test_audits_reports_cleanup_survive_fault(web, database, monkeypatch, fault, audit_fails):
    wa, client = web
    monkeypatch.setattr(wa, "_new_job_id", lambda: "syntheticjob00001")
    if audit_fails:

        def failed(*args, **kwargs):
            raise wa.AuditError("synthetic expected audit failure")

        monkeypatch.setattr(wa, "run_audit_for_uploaded_file", failed)
    baseline = snapshot_audit(wa, client)
    assert baseline["state"] == ("failed" if audit_fails else "complete")
    cleanup = []
    monkeypatch.setattr(wa, "_after_audit_task", lambda job_id: cleanup.append(job_id))
    collector = manual_collector(database)
    release = threading.Event()
    locked = None
    if fault in ("missing", "readonly", "corrupt"):
        collector._disconnect()
        if fault == "missing":
            database.unlink()
        elif fault == "readonly":
            database.chmod(0o400)
        else:
            database.write_bytes(b"SYNTHETIC_CORRUPT_DATABASE")
        with pytest.raises((OSError, ValueError, sqlite3.DatabaseError)):
            collector._tick()
        collector._accepting = False
    elif fault in ("full", "transaction"):

        def storage_failure(*args, **kwargs):
            raise sqlite3.OperationalError(
                "database or disk is full" if fault == "full" else "synthetic transaction failure"
            )

        monkeypatch.setattr(AggregateStore, "apply_batch", storage_failure)
        collector.emit(PageView("2030-01-01"))
        collector.clock.advance(5)
        with pytest.raises(sqlite3.OperationalError):
            collector._tick()
    elif fault == "overflow":
        for _ in range(1001):
            collector.emit(PageView("2030-01-01"))
        assert collector.queue.qsize() == 1000 and collector.dropped == 1
    elif fault in ("blocked", "terminated"):
        collector._disconnect()
        collector = BoundedCollector(database, FakeClock())
        entered = threading.Event()

        def blocked():
            collector._accepting = True
            entered.set()
            if fault == "terminated":
                raise SystemExit
            release.wait(3)

        monkeypatch.setattr(collector, "_tick", blocked)
        collector.start()
        assert entered.wait(2)
        if fault == "terminated":
            collector.thread.join(2)
            assert not collector.thread.is_alive()
    elif fault == "locked":
        locked = sqlite3.connect(database)
        locked.execute("BEGIN EXCLUSIVE")
        collector.emit(PageView("2030-01-01"))
        collector.clock.advance(5)
        with pytest.raises(sqlite3.OperationalError):
            collector._tick()
    else:
        collector.clock.mono = float("nan")
    monkeypatch.setattr(
        wa.app.state, "analytics_runtime", AnalyticsRuntime(collector, collector.clock)
    )
    try:
        actual = snapshot_audit(wa, client)
        assert actual == baseline
        assert len(cleanup) == 1
    finally:
        if locked:
            locked.rollback()
            locked.close()
        if fault in ("blocked", "terminated"):
            release.set()
            collector.stop()
        else:
            collector._disconnect()


@pytest.mark.parametrize("phase", ["before", "after"])
def test_short_crash_and_retry(database, phase):
    script = """
import os, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from njit_auditor.analytics.schema import AuditTerminal
from njit_auditor.analytics.store import AggregateStore, reduce_events
store=AggregateStore.open_existing(Path(sys.argv[1]))
now=datetime(2030,1,1,tzinfo=timezone.utc)
if sys.argv[2]=='before':
    store.db.execute('BEGIN IMMEDIATE')
    store.db.execute('INSERT INTO committed_batch VALUES(?,?)',(b'x'*16,now.isoformat()))
    store.db.execute('INSERT INTO daily_count VALUES(?,?,?,1)',
                     (store.epoch,'2030-01-01','audit_completed'))
else:
    store.apply_batch(b'x'*16,reduce_events((AuditTerminal('2030-01-01','completed',2),)),
                      False,now+timedelta(hours=47),now=now)
os._exit(19)
"""
    result = subprocess.run([sys.executable, "-c", script, str(database), phase], timeout=10)
    assert result.returncode == 19
    store = AggregateStore.open_existing(database)
    from njit_auditor.analytics.schema import AuditTerminal

    apply(store, [AuditTerminal("2030-01-01", "completed", 2)], nonce=b"x" * 16)
    assert store.db.execute("SELECT SUM(n) FROM daily_count").fetchone()[0] == 1
    assert store.db.execute("SELECT SUM(n) FROM daily_duration").fetchone()[0] == 1
    store.close()


def test_real_sqlite_readonly_and_full(database):
    store = AggregateStore.open_existing(database)
    store.db.execute("PRAGMA query_only=ON")
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        apply(store, [PageView("2030-01-01")])
    store.db.execute("PRAGMA query_only=OFF")
    pages = store.db.execute("PRAGMA page_count").fetchone()[0]
    store.db.execute(f"PRAGMA max_page_count={pages}")
    with pytest.raises(sqlite3.OperationalError, match="full"):
        for i in range(2000):
            apply(store, [PageView("2030-01-01")], nonce=i.to_bytes(16, "big"))
    # A failed batch cannot split its nonce from its count.
    assert (
        store.db.execute("SELECT SUM(n) FROM daily_count").fetchone()[0]
        == (store.db.execute("SELECT COUNT(*) FROM committed_batch").fetchone()[0])
    )
    store.close()


# Shared script runs unmodified against the immutable baseline and candidate.
DIFFERENTIAL = r"""
import json, re, sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from njit_auditor import web_app as wa
root=Path(sys.argv[1]); pdf=Path(sys.argv[2]).read_bytes()
wa.RUNTIME_DIR=root/'uploads'; wa._jobs={}; wa._new_job_id=lambda:'syntheticjob00001'
client=TestClient(wa.app,raise_server_exceptions=False)
result={'pages':{},'audits':[]}
for path in ('/','/help','/about','/rules','/healthz','/missing'):
    r=client.get(path); result['pages'][path]=[r.status_code,r.text]
result['rejected']=client.post('/audits',files={'file':('bad.txt',b'bad','text/plain')},
                               follow_redirects=False).status_code
for phase in ('success','handled','text','final_set'):
    cleanup=[];wa._after_audit_task=lambda job_id:cleanup.append(job_id)
    original_write=Path.write_text; original_set=wa._set_job
    def fail(*a,**k): raise wa.AuditError('synthetic failure')
    def write(path,*a,**k):
        if phase=='text' and path.name=='report.txt': raise RuntimeError('synthetic')
        return original_write(path,*a,**k)
    def set_job(job):
        if phase=='final_set' and job.state=='complete': raise RuntimeError('synthetic')
        return original_set(job)
    from contextlib import ExitStack
    with ExitStack() as stack:
        stack.enter_context(patch.object(Path,'write_text',write))
        stack.enter_context(patch.object(wa,'_set_job',set_job))
        if phase=='handled':stack.enter_context(patch.object(wa,'run_audit_for_uploaded_file',fail))
        r=client.post('/audits',files={'file':('synthetic.pdf',pdf,'application/pdf')},
                      follow_redirects=False)
    job=wa._get_job('syntheticjob00001'); directory=wa._job_dir(job.job_id)
    item={'response':[r.status_code,r.headers.get('location')],'state':job.state,
          'error':job.error_message,'findings':job.findings,'reports':{},'callback':cleanup}
    for name in ('report.json','report.md','report.txt'):
        path=directory/name
        if not path.exists():continue
        text=path.read_text()
        if name.endswith('.json'):
            text=json.loads(text);text['metadata'].pop('generated_at',None)
        else:text=re.sub(r'(?m)^- Generated at: .+$','- Generated at: <time>',text)
        item['reports'][name]=text
    for suffix in ('','/status','/download/json','/download/markdown','/download/text'):
        response=client.get('/audits/'+job.job_id+suffix)
        text=response.text
        # Only actual generated metadata and operational timestamps are normalized.
        for timestamp in (job.created_at,job.finished_at):
            if timestamp:text=text.replace(timestamp,'<time>')
        text=re.sub(r'("generated_at":\s*")[^"]+"',r'\1<time>"',text)
        text=re.sub(r'(?m)^- Generated at: .+$','- Generated at: <time>',text)
        item[suffix]=[response.status_code,text]
    item['removed']=wa.cleanup_expired_jobs(datetime.now(timezone.utc)
                        +timedelta(seconds=wa.JOB_TTL_SECONDS+2))
    item['remaining']=[directory.exists(),wa._get_job(job.job_id) is not None]
    result['audits'].append(item)
print(json.dumps(result,sort_keys=True))
"""


def test_immutable_baseline_differential(tmp_path):
    root = os.environ.get("ANALYTICS_BASELINE_ROOT")
    if not root:
        pytest.skip("requires explicitly prepared immutable synthetic baseline checkout")
    baseline = Path(root)
    assert (
        subprocess.check_output(
            ["git", "-C", str(baseline), "rev-parse", "HEAD"], text=True
        ).strip()
        == BASELINE
    )
    from test_analytics_web import synthetic_pdf

    pdf = tmp_path / "synthetic.pdf"
    pdf.write_bytes(synthetic_pdf())
    outputs = []
    for checkout in (baseline, ROOT):
        env = dict(
            os.environ,
            PYTHONPATH=str(checkout / "src"),
            NJIT_AUDITOR_ANALYTICS_ENABLED="0",
            NJIT_AUDITOR_WEB_ENVIRONMENT="local-dev",
        )
        result = subprocess.run(
            [sys.executable, "-c", DIFFERENTIAL, str(tmp_path), str(pdf)],
            env=env,
            cwd=tmp_path,
            text=True,
            capture_output=True,
            timeout=40,
        )
        assert result.returncode == 0, result.stderr
        outputs.append(json.loads(result.stdout))
    assert outputs[0] == outputs[1]
    assert outputs[0]["audits"][0]["state"] == "complete"
    assert outputs[0]["audits"][0]["reports"]["report.json"]["findings"]


def test_rule_and_threshold_hashes_unchanged():
    if not os.environ.get("ANALYTICS_BASELINE_ROOT"):
        pytest.skip("requires explicitly prepared immutable baseline with source history")
    # All existing source outside the explicitly modified web adapter is stronger
    # than just detector hashes: shared thresholds, models and report semantics included.
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASELINE, "--", "src", "data/processed/rules"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    checked = []
    for name in paths:
        if name == "src/njit_auditor/web_app.py":
            continue
        path = ROOT / name
        assert path.is_file(), name
        expected = subprocess.check_output(
            ["git", "rev-parse", f"{BASELINE}:{name}"], cwd=ROOT, text=True
        ).strip()
        content = path.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        assert actual == expected, name
        checked.append(name)
    assert any("/rules/" in name for name in checked)
    assert any("/specs/" in name for name in checked)


def test_production_baseline_readonly_metadata():
    root = os.environ.get("ANALYTICS_PRODUCTION_ROOT")
    if not root:
        pytest.skip("requires explicitly authorized production source/service metadata")
    production = Path(root)
    commit = subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip()
    assert commit == BASELINE
    assert not (production / "src/njit_auditor/analytics").exists()
    assert (
        subprocess.check_output(["git", "-C", root, "diff", "--name-only", "HEAD"], text=True) == ""
    )
    properties = subprocess.check_output(
        [
            "systemctl",
            "--user",
            "show",
            "thesis-auditor-web.service",
            "--property=MainPID,WorkingDirectory,ActiveState,FragmentPath,DropInPaths",
        ],
        text=True,
    )
    info = dict(line.split("=", 1) for line in properties.splitlines() if "=" in line)
    assert info["ActiveState"] == "active"
    assert Path(info["WorkingDirectory"]).resolve() == production.resolve()
    pid = int(info["MainPID"])
    assert pid > 0
    # Filter locally; never print service environment or unrelated configuration.
    environment = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    assert not any(item.startswith(b"NJIT_AUDITOR_ANALYTICS_") for item in environment)
    assert Path(f"/proc/{pid}/cwd").resolve() == production.resolve()
    for filename in [info["FragmentPath"], *info.get("DropInPaths", "").split()]:
        assert "NJIT_AUDITOR_ANALYTICS_" not in Path(filename).read_text()
    import urllib.request

    with urllib.request.urlopen("http://127.0.0.1:8000/version", timeout=5) as response:
        version = json.load(response)
    assert version["commit"] == BASELINE and version["environment"] == "production"
    assert not Path("/var/lib/njit-thesis-auditor-analytics").exists()
