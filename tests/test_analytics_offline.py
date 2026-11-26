"""Real CLI/desktop entry paths, inherited flags and no-op startup isolation."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_analytics_web import synthetic_pdf

from njit_auditor.analytics.collector import NoOpSink
from njit_auditor.analytics.runtime import AnalyticsSettings, build_runtime

ROOT = Path(__file__).resolve().parents[1]
TRAPS = r"""
import os, socket, threading, traceback
from pathlib import Path
from njit_auditor.analytics.collector import BoundedCollector, NoOpSink
from njit_auditor.analytics.store import AggregateStore, initialize_database
import njit_auditor.analytics.store as store

def forbidden(*args,**kwargs):
    with open(os.environ['ANALYTICS_TEST_TRAP_LOG'],'a') as f:f.write('ANALYTICS_BOUNDARY\n')
    raise AssertionError('analytics boundary reached outside enabled synthetic web')
AggregateStore.open_existing=classmethod(forbidden)
store.initialize_database=forbidden
BoundedCollector.start=forbidden
BoundedCollector.emit=forbidden
NoOpSink.emit=forbidden
start=threading.Thread.start

def checked_start(self,*args,**kwargs):
    if 'analytics' in self.name:forbidden()
    return start(self,*args,**kwargs)
threading.Thread.start=checked_start
connect=socket.socket.connect
analytics_root=Path(store.__file__).resolve().parent

def checked_connect(self,address):
    if any(Path(frame.filename).resolve().is_relative_to(analytics_root)
           for frame in traceback.extract_stack()):forbidden()
    return connect(self,address)
socket.socket.connect=checked_connect
"""


def subprocess_env(tmp_path, enabled="1"):
    trap = tmp_path / "trap"
    trap.mkdir()
    (trap / "sitecustomize.py").write_text(TRAPS)
    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join([str(trap), str(ROOT / "src")]),
        NJIT_AUDITOR_ANALYTICS_ENABLED=enabled,
        NJIT_AUDITOR_ANALYTICS_DB=str(tmp_path / "must-not-create" / "analytics.sqlite3"),
        NJIT_AUDITOR_WEB_ENVIRONMENT="production",
        NJIT_AUDITOR_WEB_RUNTIME_DIR=str(tmp_path / "uploads"),
        XDG_DATA_HOME=str(tmp_path / "desktop"),
        ANALYTICS_TEST_TRAP_LOG=str(tmp_path / "boundary-calls.txt"),
    )
    return env


def assert_no_analytics(tmp_path):
    assert not (tmp_path / "must-not-create").exists()
    assert not (tmp_path / "boundary-calls.txt").exists()


def test_real_cli_inherited_flags(tmp_path):
    pdf = tmp_path / "synthetic.pdf"
    pdf.write_bytes(synthetic_pdf())
    report = tmp_path / "report.json"
    result = subprocess.run(
        [sys.executable, "-m", "njit_auditor.cli", "pdf", str(pdf), "--json-out", str(report)],
        env=subprocess_env(tmp_path),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(report.read_text())["findings"]
    assert_no_analytics(tmp_path)


DESKTOP_DRIVER = r"""
import http.client,json,re,socket,sys,threading,urllib.parse,webbrowser
from pathlib import Path
from njit_auditor import offline_launcher,desktop_executor
finished=threading.Event(); original_run=desktop_executor.DesktopExecutor.run

def instrumented(self,job_id):
    try:return original_run(self,job_id)
    finally:finished.set()
desktop_executor.DesktopExecutor.run=instrumented

class LocalConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.settimeout(15)
        self.sock.connect(('127.0.0.1',self.port))

def drive(url):
    parsed=urllib.parse.urlparse(url); connection=LocalConnection('127.0.0.1',parsed.port)
    connection.request('GET',parsed.path+'?'+parsed.query)
    response=connection.getresponse();response.read()
    cookie=response.getheader('set-cookie').split(';',1)[0]
    connection.request('GET','/',headers={'Cookie':cookie})
    response=connection.getresponse();html=response.read().decode();assert response.status==200
    csrf=re.search(r'name="csrf_token" value="([^"]+)"',html).group(1)
    boundary='synthetic-boundary'
    body=('--'+boundary+'\r\nContent-Disposition: form-data; name="csrf_token"\r\n\r\n'
          +csrf+'\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="file"; '
          'filename="synthetic.pdf"\r\nContent-Type: application/pdf\r\n\r\n').encode()
    body+=Path(sys.argv[1]).read_bytes()+('\r\n--'+boundary+'--\r\n').encode()
    headers={'Cookie':cookie,'Origin':f'http://127.0.0.1:{parsed.port}',
             'Content-Type':'multipart/form-data; boundary='+boundary}
    connection.request('POST','/audits',body,headers)
    response=connection.getresponse();response.read();assert response.status==303
    location=response.getheader('location')
    assert finished.wait(20),'synthetic desktop audit timed out'
    connection.request('GET',location+'/download/json',headers={'Cookie':cookie})
    response=connection.getresponse();report=json.loads(response.read());assert response.status==200
    assert report['findings']
    connection.request('POST','/quit','csrf_token='+csrf,{'Cookie':cookie,
        'Origin':f'http://127.0.0.1:{parsed.port}','Content-Type':'application/x-www-form-urlencoded'})
    response=connection.getresponse();response.read();assert response.status==200
    connection.close()
    return True
webbrowser.open=drive
# Real entry function, real Uvicorn/socket/session and real worker subprocess.
# Only external GUI presentation is replaced with the synthetic HTTP driver.
saved=sys.argv[1]
sys.argv=['njit-offline','--headless']
# The driver's input path is independent of the launcher's argument parsing.
original_drive=drive
webbrowser.open=lambda url: (sys.argv.append(saved),original_drive(url))[1]
offline_launcher.main()
assert not any('analytics' in t.name for t in threading.enumerate())
"""


def test_real_desktop_launcher_inherited_flags(tmp_path):
    pdf = tmp_path / "synthetic.pdf"
    pdf.write_bytes(synthetic_pdf())
    # Driver retains the PDF path separately because main parses its own argv.
    script = DESKTOP_DRIVER.replace("Path(sys.argv[1]).read_bytes()", "Path(saved).read_bytes()")
    result = subprocess.run(
        [sys.executable, "-c", script, str(pdf)],
        env=subprocess_env(tmp_path),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=40,
    )
    assert result.returncode == 0, result.stderr
    assert_no_analytics(tmp_path)
    assert not list((tmp_path / "desktop").rglob("upload.pdf"))


def test_disabled_import_and_lifespan_no_boundary(tmp_path):
    script = """
import threading
from fastapi.testclient import TestClient
from njit_auditor.web_app import app
with TestClient(app) as client:
    assert client.get('/').status_code==200
assert not any('analytics' in t.name for t in threading.enumerate())
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=subprocess_env(tmp_path, "0"),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert_no_analytics(tmp_path)


@pytest.mark.parametrize("flag", ["", "0", "true", "yes", "01", " 1", "1 "])
def test_only_exact_one_requests_enable(monkeypatch, flag):
    monkeypatch.setenv("NJIT_AUDITOR_ANALYTICS_ENABLED", flag)
    monkeypatch.setenv("NJIT_AUDITOR_ANALYTICS_DB", "/tmp/synthetic.sqlite3")
    assert not AnalyticsSettings.from_environment(public_web=True, environment="production").enabled


@pytest.mark.parametrize("mode", ["offline", "desktop", "cli", "test", "local-dev"])
def test_explicit_settings_cannot_override_offline(mode, tmp_path):
    runtime = build_runtime(AnalyticsSettings(True, tmp_path / "trap.sqlite3"), app_mode=mode)
    runtime.start()
    assert isinstance(runtime.sink, NoOpSink)
    assert not list(tmp_path.iterdir())


def test_environment_requires_public_production(monkeypatch):
    monkeypatch.setenv("NJIT_AUDITOR_ANALYTICS_ENABLED", "1")
    monkeypatch.setenv("NJIT_AUDITOR_ANALYTICS_DB", "/tmp/synthetic.sqlite3")
    assert not AnalyticsSettings.from_environment(
        public_web=False, environment="production"
    ).enabled
    assert not AnalyticsSettings.from_environment(public_web=True, environment="local-dev").enabled
    assert AnalyticsSettings.from_environment(public_web=True, environment="production").enabled
    monkeypatch.delenv("NJIT_AUDITOR_ANALYTICS_DB")
    assert not AnalyticsSettings.from_environment(public_web=True, environment="production").enabled


def test_ordinary_testclient_inherited_production_flags(tmp_path):
    script = r"""
import sys
from fastapi.testclient import TestClient
from njit_auditor import web_app as wa
from njit_auditor.analytics.collector import NoOpSink
assert 'pytest' not in sys.modules
with TestClient(wa.app) as client:
    assert isinstance(wa.app.state.analytics_runtime.sink, NoOpSink)
    assert client.get('/').status_code == 200
"""
    env = subprocess_env(tmp_path)
    env.pop("PYTEST_CURRENT_TEST", None)
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert_no_analytics(tmp_path)


@pytest.mark.parametrize("checkout_name", ["analytics", "ordinary-checkout"])
def test_isolation_independent_of_checkout_name(tmp_path, monkeypatch, checkout_name):
    import shutil

    checkout = tmp_path / checkout_name
    shutil.copytree(ROOT / "src", checkout / "src", ignore=shutil.ignore_patterns("__pycache__"))
    for resource in ("assets", "data/processed", "data/specs"):
        source = ROOT / resource
        if source.exists():
            target = checkout / resource
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source, target_is_directory=True)
    monkeypatch.setattr(sys.modules[__name__], "ROOT", checkout)
    for check in (test_real_cli_inherited_flags, test_real_desktop_launcher_inherited_flags,
                  test_disabled_import_and_lifespan_no_boundary,
                  test_ordinary_testclient_inherited_production_flags):
        directory = tmp_path / check.__name__
        directory.mkdir()
        check(directory)


def test_network_trap_identifies_only_actual_analytics_package(tmp_path):
    script = r"""
import socket
from pathlib import Path
import sitecustomize as traps
# Replace only the final OS call: no test network connection is made.
traps.connect=lambda *args: None
code="with socket.socket() as sock: sock.connect(('127.0.0.1', 9))"
for path in [Path.cwd()/'analytics'/'unrelated.py',
             traps.analytics_root.parent/'analytics_other'/'probe.py']:
    exec(compile(code,str(path),'exec'))
assert not Path(traps.os.environ['ANALYTICS_TEST_TRAP_LOG']).exists()
try:
    exec(compile(code,str(traps.analytics_root/'probe.py'),'exec'))
except AssertionError:
    pass
else:
    raise AssertionError('actual analytics package network call escaped the trap')
assert Path(traps.os.environ['ANALYTICS_TEST_TRAP_LOG']).read_text()=='ANALYTICS_BOUNDARY\n'
"""
    result = subprocess.run(
        [sys.executable, "-c", script], env=subprocess_env(tmp_path), cwd=tmp_path,
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
