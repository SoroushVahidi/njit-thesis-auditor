"""Local event-loop traffic is allowed; remote, DNS and worker traffic is not."""

import asyncio
import ipaddress
import socket

import pytest

from njit_auditor.desktop_network import restrict_network


@pytest.fixture()
def guard(monkeypatch):
    # Record every patched entry point so the process-wide policy is restored.
    for owner, names in (
        (socket.socket, ("connect", "connect_ex")),
        (socket, ("create_connection", "getaddrinfo", "gethostbyname", "gethostbyname_ex")),
    ):
        for name in names:
            monkeypatch.setattr(owner, name, getattr(owner, name))
    return restrict_network


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
def test_ui_allows_real_loopback_wakeup_pair(guard, method):
    guard(allow_loopback=True)
    with socket.socket() as listener, socket.socket() as client:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client.settimeout(2)
        result = getattr(client, method)(listener.getsockname())
        assert result in (None, 0)
        with listener.accept()[0] as server:
            server.settimeout(2)
            client.sendall(b"wakeup")
            assert server.recv(6) == b"wakeup"
    # Exercises the actual Proactor socket pair on Windows, selector on Linux.
    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(asyncio.sleep(0, result="ready")) == "ready"
    finally:
        loop.close()


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
@pytest.mark.parametrize(
    "host",
    ["192.0.2.1", "192.168.1.1", "0.0.0.0", "localhost", "127.0.0.1.example.invalid", "2130706433"],
)
def test_ui_rejects_non_loopback_and_hostnames_before_connecting(guard, method, host):
    guard(allow_loopback=True)
    with socket.socket() as client:
        with pytest.raises(OSError, match="Network requests are unavailable"):
            getattr(client, method)((host, 80))


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
@pytest.mark.parametrize("host", ["::", "2001:db8::1", "::ffff:127.0.0.1"])
def test_ui_rejects_non_loopback_ipv6(guard, method, host):
    guard(allow_loopback=True)
    with socket.socket(socket.AF_INET6) as client:
        with pytest.raises(OSError, match="Network requests are unavailable"):
            getattr(client, method)((host, 80))


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
def test_mapped_ipv6_rejected_independent_of_python_classification(guard, monkeypatch, method):
    # Reproduce the newer Windows Python's classification on older Python too.
    monkeypatch.setattr(ipaddress.IPv6Address, "is_loopback", property(lambda _: True))
    guard(allow_loopback=True)
    with socket.socket(socket.AF_INET6) as client:
        with pytest.raises(OSError, match="Network requests are unavailable"):
            getattr(client, method)(("::ffff:127.0.0.1", 80))


@pytest.mark.parametrize("allow_loopback", [False, True])
def test_dns_and_high_level_connections_remain_blocked(guard, allow_loopback):
    guard(allow_loopback=allow_loopback)
    calls = [
        lambda: socket.getaddrinfo("example.invalid", 80),
        lambda: socket.gethostbyname("example.invalid"),
        lambda: socket.gethostbyname_ex("example.invalid"),
        lambda: socket.create_connection(("127.0.0.1", 80)),
    ]
    for call in calls:
        with pytest.raises(OSError, match="Network requests are unavailable"):
            call()


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
def test_worker_denies_even_loopback(guard, method):
    guard()
    with socket.socket() as client:
        with pytest.raises(OSError, match="Network requests are unavailable"):
            getattr(client, method)(("127.0.0.1", 80))
