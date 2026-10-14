"""Network throughput sources for VIDAA Eco's in-app idle detection.

Why this exists
---------------
A VIDAA TV reports *which* app is open, but not whether that app is actually
playing. A paused Netflix and a playing Netflix look identical over the TV's
own protocol. The only reliable tell is network traffic: a streaming app pulls
megabits per second, a paused/idle one almost nothing.

The TV does not report its own traffic, so VIDAA Eco reads it from another
Home Assistant integration that does - typically your router / access points
(UniFi Network "bandwidth sensors", AVM FRITZ!Box, OpenWrt/luci, SNMP, ...).

How sources are chosen (in order)
---------------------------------
1. **Manual** - the sensors picked in the integration's options
   (``throughput_sensors``; older entries may still hold one ``throughput_sensor``).
   Pick several when the TV can use more than one interface (Wi-Fi *and*
   Ethernet MAC) or when a router exposes download and upload separately -
   they are summed.
2. **Automatic** (default on) - when nothing is picked, VIDAA Eco looks for
   data-rate sensors on any *other* Home Assistant device that shares one of
   this TV's MAC addresses (that is how router integrations model clients).
3. **None** - in-app idle detection is off: an open app never counts as idle.

Values are converted to kbit/s whatever unit the source uses (bit/s ... GB/s).

This module has no Home Assistant imports at module level so the pure helpers
can be unit-tested without Home Assistant installed.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

# Home Assistant UnitOfDataRate values -> factor to kbit/s.
_TO_KBPS: dict[str, float] = {
    "bit/s": 0.001,
    "kbit/s": 1.0,
    "Mbit/s": 1_000.0,
    "Gbit/s": 1_000_000.0,
    "B/s": 0.008,
    "kB/s": 8.0,
    "MB/s": 8_000.0,
    "GB/s": 8_000_000.0,
    "KiB/s": 8.192,
    "MiB/s": 8_388.608,
    "GiB/s": 8_589_934.592,
}

MODE_MANUAL = "manual"
MODE_AUTO = "auto"
MODE_NONE = "none"

_HEX12 = re.compile(r"^[0-9a-f]{12}$")

# Data-rate sensors that describe a link's *capacity*, not its traffic (e.g. a
# 1000 Mbit/s "link speed"). Summing those would make the TV look busy forever.
_NOT_TRAFFIC = re.compile(r"link|speed|capacity|max|limit|negotiat|phy", re.IGNORECASE)


def normalize_mac(value: Any) -> str | None:
    """Return a MAC as lower-case aa:bb:cc:dd:ee:ff, or None if it is not one."""
    if not value or not isinstance(value, str):
        return None
    hexchars = re.sub(r"[^0-9a-fA-F]", "", value).lower()
    if not _HEX12.match(hexchars):
        return None
    return ":".join(hexchars[i:i + 2] for i in range(0, 12, 2))


def to_kbps(value: Any, unit: str | None) -> float | None:
    """Convert a sensor reading to kbit/s. Unknown/missing unit = already kbit/s."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    factor = _TO_KBPS.get(unit or "kbit/s")
    if factor is None:
        return None
    return number * factor


def is_data_rate_unit(unit: str | None) -> bool:
    """True when the unit is one of Home Assistant's data-rate units."""
    return bool(unit) and unit in _TO_KBPS


def configured_sources(options: dict) -> list[str]:
    """Sensors the user picked (new list option, plus the legacy single option)."""
    picked: list[str] = []
    for eid in list(options.get("throughput_sensors") or []) + [options.get("throughput_sensor")]:
        if isinstance(eid, str) and eid and eid not in picked:
            picked.append(eid)
    return picked


def tv_macs(data: dict) -> set[str]:
    """Every MAC address the config entry knows for this TV."""
    keys = ("mac", "hw_mac", "mac_ethernet", "mac_wifi", "device_id")
    return {m for m in (normalize_mac(data.get(k)) for k in keys) if m}


def discover_sources(hass, entry, own_device_ids: Iterable[str] = ()) -> list[str]:
    """Data-rate sensors on other HA devices that share one of this TV's MACs."""
    from homeassistant.helpers import device_registry as dr, entity_registry as er

    macs = tv_macs(dict(entry.data))
    if not macs:
        return []
    own = set(own_device_ids)
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    found: list[str] = []
    for device in dev_reg.devices.values():
        if device.id in own or entry.entry_id in device.config_entries:
            continue
        conn_macs = {
            normalize_mac(value)
            for kind, value in device.connections
            if kind == dr.CONNECTION_NETWORK_MAC
        }
        if not conn_macs & macs:
            continue
        for ent in er.async_entries_for_device(ent_reg, device.id):
            if ent.domain != "sensor" or ent.disabled_by is not None:
                continue
            device_class = ent.device_class or ent.original_device_class
            state = hass.states.get(ent.entity_id)
            unit = state.attributes.get("unit_of_measurement") if state else ent.unit_of_measurement
            label = " ".join(
                str(x) for x in (ent.entity_id, ent.unique_id, ent.original_name, ent.name) if x
            )
            if _NOT_TRAFFIC.search(label):
                continue
            if device_class == "data_rate" or is_data_rate_unit(unit):
                found.append(ent.entity_id)
    return sorted(found)


def read_total_kbps(hass, sources: Iterable[str]) -> tuple[float | None, dict[str, float | None]]:
    """Sum the sources in kbit/s. None when no source currently has a number."""
    per_source: dict[str, float | None] = {}
    total = 0.0
    any_value = False
    for eid in sources:
        state = hass.states.get(eid)
        if state is None or state.state in ("unknown", "unavailable", "", None):
            per_source[eid] = None
            continue
        kbps = to_kbps(state.state, state.attributes.get("unit_of_measurement"))
        per_source[eid] = None if kbps is None else round(kbps, 1)
        if kbps is not None:
            total += kbps
            any_value = True
    return (round(total, 1) if any_value else None), per_source
