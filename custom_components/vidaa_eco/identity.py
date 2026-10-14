"""Stable per-TV identity (device_id) for VIDAA Eco.

The device_id is the registry identifier of the TV's device and the prefix of
every entity unique_id, so it must be stable and unique per TV.

Historically it was read from the TV's ``getdeviceinfo`` field
``network_type``, which on many firmwares holds the Wi-Fi MAC without colons
(e.g. ``10b232af57d4``). Other firmwares (seen on a 58A60 / V0000.09.61B)
return the literal interface name ``"wlan"`` there instead - so every such TV
got the same id. :func:`tv_device_id` only accepts a real 12-hex-digit value and
otherwise falls back to the TV's own MAC addresses.
"""
from __future__ import annotations

import re
from typing import Any

_HEX12 = re.compile(r"^[0-9a-f]{12}$")


def bare_mac(value: Any) -> str | None:
    """Return a MAC as 12 lower-case hex digits, or None if it is not one."""
    if not value or not isinstance(value, str):
        return None
    hexchars = re.sub(r"[^0-9a-fA-F]", "", value).lower()
    return hexchars if _HEX12.match(hexchars) else None


def is_valid_device_id(value: Any) -> bool:
    """True when value already is a bare 12-hex-digit MAC-style id."""
    return isinstance(value, str) and bool(_HEX12.match(value))


def tv_device_id(info: dict | None, *fallback_macs: Any) -> str | None:
    """Best stable id: network_type if it is a MAC, else the first valid fallback MAC.

    Fallbacks should be given most-preferred first: Wi-Fi MAC (matches what
    network_type holds on firmwares that report it), then Ethernet, then the
    hardware MAC.
    """
    candidate = bare_mac((info or {}).get("network_type"))
    if candidate:
        return candidate
    for mac in fallback_macs:
        candidate = bare_mac(mac)
        if candidate:
            return candidate
    return None
