"""Loopback-only network guard.

The README promises that nothing leaves the machine. A promise is not a
guarantee, so the promise lives here as code that can fail:

* ``is_loopback_address`` is what the audit-hook probe uses to judge a target.
* ``assert_loopback_host`` is what the server uses to refuse a public bind.

Both are pure functions on purpose: a privacy claim that can only be checked by
starting a server and watching ``lsof`` is an experiment, not a test.
"""

from __future__ import annotations

import ipaddress

# Names that always mean "this machine". Kept explicit instead of relying on a
# DNS lookup: resolving ``localhost`` is fine, resolving anything else is the
# leak we are trying to catch.
_LOOPBACK_NAMES = frozenset(
    {"", "localhost", "localhost.localdomain", "localhost4", "localhost6"}
)


class LocalOnlyViolation(RuntimeError):
    """Raised when something asks for a non-loopback network destination."""


def _is_loopback_host(host: str) -> bool:
    """True for loopback names and loopback IP literals (v4 or v6)."""
    h = host.split("%")[0].strip().strip("[]").lower()
    if h in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        # A hostname that is not a loopback name would need DNS, and DNS is
        # already traffic. Treat it as non-local.
        return False


def is_loopback_address(address: object) -> bool:
    """Judge a socket target: ``(host, port)``, a bare host, or a UNIX path."""
    if address is None or address is True:
        return True
    if isinstance(address, bytes):
        # AF_UNIX abstract namespace: stays on the machine by definition.
        return True
    if isinstance(address, str):
        if address.startswith("/"):
            return True  # filesystem socket
        return _is_loopback_host(address)
    if isinstance(address, (tuple, list)):
        if not address:
            return True
        return is_loopback_address(address[0])
    return True


def assert_loopback_host(host: str) -> str:
    """Return ``host`` when it is loopback, raise otherwise."""
    if not is_loopback_address(host):
        raise LocalOnlyViolation(
            f"refusing to bind {host!r}: this app is local-only by design. "
            "Use 127.0.0.1 (or ::1). Exposing it on a network interface "
            "removes the only privacy guarantee the project makes."
        )
    return host
