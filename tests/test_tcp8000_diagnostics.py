from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "inspect_tcp8000_diagnostics.py"
_SPEC = importlib.util.spec_from_file_location("inspect_tcp8000_diagnostics", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
diag = importlib.util.module_from_spec(_SPEC)
sys.modules["inspect_tcp8000_diagnostics"] = diag
_SPEC.loader.exec_module(diag)


def test_parse_tcpdump_syn_line() -> None:
    line = (
        "2026-07-20 13:01:02.123456 IP 10.196.115.152.51544 > "
        "10.196.93.210.8000: Flags [S], seq 1, win 64240, length 0"
    )

    event = diag.parse_tcpdump_line(line)

    assert event is not None
    assert event.src_ip == "10.196.115.152"
    assert event.src_port == 51544
    assert event.dst_ip == "10.196.93.210"
    assert event.dst_port == 8000
    assert event.flags == "S"
    assert event.length == 0


def test_summarize_successful_handshake() -> None:
    lines = [
        (
            "2026-07-20 13:01:02.100000 IP 10.196.115.152.51544 > "
            "10.196.93.210.8000: Flags [S], length 0"
        ),
        (
            "2026-07-20 13:01:02.101000 IP 10.196.93.210.8000 > "
            "10.196.115.152.51544: Flags [S.], length 0"
        ),
        (
            "2026-07-20 13:01:02.102000 IP 10.196.115.152.51544 > "
            "10.196.93.210.8000: Flags [.], length 0"
        ),
        (
            "2026-07-20 13:01:02.103000 IP 10.196.115.152.51544 > "
            "10.196.93.210.8000: Flags [P.], length 84"
        ),
    ]
    events = [event for line in lines if (event := diag.parse_tcpdump_line(line)) is not None]

    summaries = diag.summarize_connections(
        events,
        client_ip="10.196.115.152",
        server_ip="10.196.93.210",
        server_port=8000,
    )

    summary = summaries[51544]
    assert summary.syn_seen is True
    assert summary.synack_seen is True
    assert summary.ack_after_synack_seen is True
    assert summary.client_payload_packets == 1


def test_summarize_reset_and_fin_flags() -> None:
    lines = [
        (
            "2026-07-20 13:01:02.100000 IP 10.196.115.152.51544 > "
            "10.196.93.210.8000: Flags [R], length 0"
        ),
        (
            "2026-07-20 13:01:03.100000 IP 10.196.115.152.51545 > "
            "10.196.93.210.8000: Flags [F.], length 0"
        ),
    ]
    events = [event for line in lines if (event := diag.parse_tcpdump_line(line)) is not None]

    summaries = diag.summarize_connections(
        events,
        client_ip="10.196.115.152",
        server_ip="10.196.93.210",
        server_port=8000,
    )

    assert summaries[51544].reset_seen is True
    assert summaries[51545].fin_seen is True


def test_render_report_distinguishes_no_syn() -> None:
    report = diag.render_report(
        client_ip="10.196.115.152",
        server_ip="10.196.93.210",
        server_port=8000,
        tcp_log=Path("/var/log/njit-thesis-auditor/tcp-8000.log"),
        events=[],
        summaries={},
        app_lines=[],
        journal_warning="",
        show_lines=False,
    )

    assert "SYN seen: no" in report
    assert "HTTP access log lines for client: 0" in report
