"""
Network connection detection utilities.

This module exposes helpers that check whether the current host appears to have
network connectivity. The check first tries to establish a socket connection to
well-known public DNS servers and falls back to inspecting the routing table.
"""

from __future__ import annotations

import socket
import subprocess
from typing import Iterable, Optional, Tuple

from until.log import LOGGER

# Hosts that are typically reachable whenever the internet is available.
DEFAULT_TEST_TARGETS: Tuple[Tuple[str, int], ...] = (
    ("8.8.8.8", 53),      # Google DNS
    ("1.1.1.1", 53),      # Cloudflare DNS
    ("114.114.114.114", 53),  # Chinese public DNS
)


def _can_reach_host(host: str, port: int, timeout: float) -> bool:
    """
    Attempt to open a TCP socket to a remote host.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError as exc:
        LOGGER.debug(f"network_detect: failed to reach {host}:{port} ({exc})")
        return False


def _get_default_gateway() -> Optional[str]:
    """
    Parse the system routing table to find the default gateway IP.
    """
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        LOGGER.debug("network_detect: 'ip' command not available")
        return None

    if result.returncode != 0:
        LOGGER.debug(f"network_detect: 'ip route' failed with {result.returncode}")
        return None

    for line in result.stdout.splitlines():
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] != "default":
            continue
        if "via" in tokens:
            via_index = tokens.index("via") + 1
            if via_index < len(tokens):
                return tokens[via_index]
    return None


def is_network_connected(
    targets: Iterable[Tuple[str, int]] = DEFAULT_TEST_TARGETS, timeout: float = 2.0
) -> bool:
    """
    Determine whether the system is connected to a network.

    The method will try to open short-lived TCP sockets to a list of known hosts.
    If each attempt fails, it falls back to checking whether a default route
    exists. Returns True if any check succeeds.
    """
    for host, port in targets:
        if _can_reach_host(host, port, timeout):
            return True

    gateway = _get_default_gateway()
    if gateway:
        if _can_reach_host(gateway, 53, timeout):
            return True
        # Even if the router does not expose DNS, the presence of the default
        # route itself indicates LAN connectivity.
        return True

    return False
