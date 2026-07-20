#!/usr/bin/env python3
"""Summarize metadata-only TCP/8000 diagnostics and optional Uvicorn access logs."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

DEFAULT_TCP_LOG = Path("/var/log/njit-thesis-auditor/tcp-8000.log")
DEFAULT_SERVER_IP = "10.196.93.210"
DEFAULT_PORT = 8000
DEFAULT_JOURNAL_UNIT = "thesis-auditor-web.service"

_TCPDUMP_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
    r"IP\s+(?P<src>\S+)\s+>\s+(?P<dst>\S+):\s+Flags\s+\[(?P<flags>[^\]]*)\]"
)


@dataclass(frozen=True)
class TcpEvent:
    timestamp: datetime
    raw_timestamp: str
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    flags: str
    length: int | None
    raw_line: str


@dataclass
class ConnectionSummary:
    client_port: int
    first_seen: datetime
    last_seen: datetime
    syn_seen: bool = False
    synack_seen: bool = False
    ack_after_synack_seen: bool = False
    client_payload_packets: int = 0
    server_payload_packets: int = 0
    reset_seen: bool = False
    fin_seen: bool = False
    events: list[TcpEvent] = field(default_factory=list)

    def add(self, event: TcpEvent, *, client_ip: str, server_ip: str, server_port: int) -> None:
        self.first_seen = min(self.first_seen, event.timestamp)
        self.last_seen = max(self.last_seen, event.timestamp)
        self.events.append(event)

        client_to_server = (
            event.src_ip == client_ip
            and event.dst_ip == server_ip
            and event.dst_port == server_port
        )
        server_to_client = (
            event.src_ip == server_ip
            and event.src_port == server_port
            and event.dst_ip == client_ip
        )

        if client_to_server and "S" in event.flags and "." not in event.flags:
            self.syn_seen = True
        if server_to_client and "S" in event.flags and "." in event.flags:
            self.synack_seen = True
        if client_to_server and self.synack_seen and "." in event.flags and "S" not in event.flags:
            self.ack_after_synack_seen = True
        if client_to_server and (event.length or 0) > 0:
            self.client_payload_packets += 1
        if server_to_client and (event.length or 0) > 0:
            self.server_payload_packets += 1
        if "R" in event.flags:
            self.reset_seen = True
        if "F" in event.flags:
            self.fin_seen = True


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("T", " ")
    return datetime.fromisoformat(normalized)


def _split_ipv4_port(value: str) -> tuple[str, int] | None:
    clean = value.rstrip(":")
    host, sep, port_text = clean.rpartition(".")
    if not sep or not host or not port_text.isdigit():
        return None
    if len(host.split(".")) != 4:
        return None
    return host, int(port_text)


def parse_tcpdump_line(line: str) -> TcpEvent | None:
    match = _TCPDUMP_RE.match(line.strip())
    if not match:
        return None
    src = _split_ipv4_port(match.group("src"))
    dst = _split_ipv4_port(match.group("dst"))
    if src is None or dst is None:
        return None
    length_match = re.search(r"\blength\s+(\d+)\b", line)
    length_text = length_match.group(1) if length_match else None
    return TcpEvent(
        timestamp=datetime.fromisoformat(match.group("ts")),
        raw_timestamp=match.group("ts"),
        src_ip=src[0],
        src_port=src[1],
        dst_ip=dst[0],
        dst_port=dst[1],
        flags=match.group("flags"),
        length=int(length_text) if length_text is not None else None,
        raw_line=line.rstrip("\n"),
    )


def load_tcp_events(
    path: Path,
    *,
    client_ip: str,
    server_ip: str,
    server_port: int,
    since: datetime | None,
    until: datetime | None,
) -> list[TcpEvent]:
    events: list[TcpEvent] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        event = parse_tcpdump_line(line)
        if event is None:
            continue
        if since is not None and event.timestamp < since:
            continue
        if until is not None and event.timestamp > until:
            continue
        involves_client = event.src_ip == client_ip or event.dst_ip == client_ip
        involves_server = event.src_ip == server_ip or event.dst_ip == server_ip
        involves_port = event.src_port == server_port or event.dst_port == server_port
        if involves_client and involves_server and involves_port:
            events.append(event)
    return events


def summarize_connections(
    events: list[TcpEvent],
    *,
    client_ip: str,
    server_ip: str,
    server_port: int,
) -> dict[int, ConnectionSummary]:
    summaries: dict[int, ConnectionSummary] = {}
    for event in sorted(events, key=lambda item: item.timestamp):
        if event.src_ip == client_ip:
            client_port = event.src_port
        elif event.dst_ip == client_ip:
            client_port = event.dst_port
        else:
            continue
        summary = summaries.setdefault(
            client_port,
            ConnectionSummary(
                client_port=client_port,
                first_seen=event.timestamp,
                last_seen=event.timestamp,
            ),
        )
        summary.add(event, client_ip=client_ip, server_ip=server_ip, server_port=server_port)
    return summaries


def _load_app_log_lines_from_file(
    path: Path,
    *,
    client_ip: str,
    since: datetime | None,
    until: datetime | None,
) -> list[str]:
    if not path.exists():
        return []
    matched: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if client_ip not in line:
            continue
        timestamp = _extract_any_timestamp(line)
        if timestamp is not None:
            if since is not None and timestamp < since:
                continue
            if until is not None and timestamp > until:
                continue
        matched.append(line)
    return matched


def _extract_any_timestamp(line: str) -> datetime | None:
    match = re.search(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?", line)
    if not match:
        return None
    try:
        return datetime.fromisoformat(match.group(0).replace("T", " "))
    except ValueError:
        return None


def _load_app_log_lines_from_journal(
    *,
    unit: str,
    client_ip: str,
    since_text: str | None,
    until_text: str | None,
) -> tuple[list[str], str]:
    cmd = ["journalctl", "--user", "-u", unit, "--no-pager", "-o", "short-iso"]
    if since_text:
        cmd.extend(["--since", since_text])
    if until_text:
        cmd.extend(["--until", until_text])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return [], f"journalctl unavailable: {exc}"
    lines = [line for line in result.stdout.splitlines() if client_ip in line]
    warning = ""
    if result.returncode != 0:
        warning = result.stderr.strip() or f"journalctl exited with {result.returncode}"
    return lines, warning


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def render_report(
    *,
    client_ip: str,
    server_ip: str,
    server_port: int,
    tcp_log: Path,
    events: list[TcpEvent],
    summaries: dict[int, ConnectionSummary],
    app_lines: list[str],
    journal_warning: str,
    show_lines: bool,
) -> str:
    lines: list[str] = []
    lines.append("TCP/8000 diagnostic summary")
    lines.append(f"client_ip: {client_ip}")
    lines.append(f"server: {server_ip}:{server_port}")
    lines.append(f"tcp_log: {tcp_log}")
    lines.append(f"tcp_events_matched: {len(events)}")
    lines.append(f"connections_observed: {len(summaries)}")
    lines.append("")

    any_syn = any(summary.syn_seen for summary in summaries.values())
    any_synack = any(summary.synack_seen for summary in summaries.values())
    any_ack = any(summary.ack_after_synack_seen for summary in summaries.values())
    lines.append(f"SYN seen: {_yes_no(any_syn)}")
    lines.append(f"SYN-ACK seen: {_yes_no(any_synack)}")
    lines.append(f"client ACK after SYN-ACK seen: {_yes_no(any_ack)}")
    lines.append(f"HTTP access log lines for client: {len(app_lines)}")
    if journal_warning:
        lines.append(f"journal warning: {journal_warning}")
    lines.append("")

    if summaries:
        lines.append("Per-client-port TCP observations:")
        for port, summary in sorted(summaries.items()):
            lines.append(
                "  "
                f"{client_ip}:{port} "
                f"first={summary.first_seen.isoformat(sep=' ')} "
                f"last={summary.last_seen.isoformat(sep=' ')} "
                f"syn={_yes_no(summary.syn_seen)} "
                f"synack={_yes_no(summary.synack_seen)} "
                f"ack={_yes_no(summary.ack_after_synack_seen)} "
                f"client_payload_packets={summary.client_payload_packets} "
                f"server_payload_packets={summary.server_payload_packets} "
                f"rst={_yes_no(summary.reset_seen)} "
                f"fin={_yes_no(summary.fin_seen)}"
            )
    else:
        lines.append("No TCP events matched the requested client/server/port window.")

    if show_lines:
        lines.append("")
        lines.append("Matching tcpdump lines:")
        lines.extend(f"  {event.raw_line}" for event in events)
        lines.append("")
        lines.append("Matching application log lines:")
        lines.extend(f"  {line}" for line in app_lines)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-ip", default="10.196.115.152")
    parser.add_argument("--server-ip", default=DEFAULT_SERVER_IP)
    parser.add_argument("--server-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--tcp-log", type=Path, default=DEFAULT_TCP_LOG)
    parser.add_argument("--since", help="Local time, e.g. '2026-07-20 13:00:00'")
    parser.add_argument("--until", help="Local time, e.g. '2026-07-20 13:15:00'")
    parser.add_argument("--app-log", type=Path, help="Optional Uvicorn text log to scan")
    parser.add_argument(
        "--journal-unit",
        default=DEFAULT_JOURNAL_UNIT,
        help="User-level systemd unit to scan with journalctl --user; use '' to skip",
    )
    parser.add_argument("--show-lines", action="store_true")
    args = parser.parse_args()

    since = _parse_time(args.since)
    until = _parse_time(args.until)
    events = load_tcp_events(
        args.tcp_log,
        client_ip=args.client_ip,
        server_ip=args.server_ip,
        server_port=args.server_port,
        since=since,
        until=until,
    )
    summaries = summarize_connections(
        events,
        client_ip=args.client_ip,
        server_ip=args.server_ip,
        server_port=args.server_port,
    )

    app_lines: list[str] = []
    journal_warning = ""
    if args.app_log:
        app_lines.extend(
            _load_app_log_lines_from_file(
                args.app_log,
                client_ip=args.client_ip,
                since=since,
                until=until,
            )
        )
    if args.journal_unit:
        journal_lines, journal_warning = _load_app_log_lines_from_journal(
            unit=args.journal_unit,
            client_ip=args.client_ip,
            since_text=args.since,
            until_text=args.until,
        )
        app_lines.extend(journal_lines)

    print(
        render_report(
            client_ip=args.client_ip,
            server_ip=args.server_ip,
            server_port=args.server_port,
            tcp_log=args.tcp_log,
            events=events,
            summaries=summaries,
            app_lines=app_lines,
            journal_warning=journal_warning,
            show_lines=args.show_lines,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
