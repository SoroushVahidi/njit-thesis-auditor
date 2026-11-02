"""Keep desktop networking local, including Windows asyncio's TCP socket pair."""

from __future__ import annotations

import ipaddress
import socket

_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex


def deny_network(*_args, **_kwargs):
    raise OSError("Network requests are unavailable in a desktop audit")


def is_loopback_address(family: int, address: object) -> bool:
    if family not in (socket.AF_INET, socket.AF_INET6):
        return False
    if not isinstance(address, tuple) or not address or not isinstance(address[0], str):
        return False
    try:
        host = ipaddress.ip_address(address[0])
    except ValueError:
        return False  # Hostnames are never resolved, including 'localhost'.
    return host.is_loopback and host.version == (4 if family == socket.AF_INET else 6)


def loopback_connect(sock: socket.socket, address):
    if not is_loopback_address(sock.family, address):
        deny_network()
    return _connect(sock, address)


def loopback_connect_ex(sock: socket.socket, address):
    if not is_loopback_address(sock.family, address):
        deny_network()
    return _connect_ex(sock, address)


def restrict_network(*, allow_loopback: bool = False) -> None:
    # The UI event loop needs literal loopback TCP on Windows. Audit workers
    # have no event loop/listener and retain the stricter deny-all policy.
    setattr(socket.socket, "connect", loopback_connect if allow_loopback else deny_network)
    setattr(socket.socket, "connect_ex", loopback_connect_ex if allow_loopback else deny_network)
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network
    socket.gethostbyname = deny_network
    socket.gethostbyname_ex = deny_network
