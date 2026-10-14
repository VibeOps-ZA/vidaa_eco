"""Device-registry lookups that work on both older and current Home Assistant.

Home Assistant 2026.x made device identifiers/connections unique per config
entry only, and deprecated ``DeviceRegistry.async_get_device``, using
``DeviceRegistry.devices`` as a mapping, and ``DeviceEntry.config_entries``
(removal in 2027.8-2027.10). These helpers use the new API when present and
fall back to the old one otherwise.
"""
from __future__ import annotations

from typing import Iterable

from homeassistant.helpers import device_registry as dr


def own_device(reg: dr.DeviceRegistry, domain: str, identifier: str, entry_id: str):
    """This config entry's device with the given identifier, or None."""
    getter = getattr(reg, "async_get_device_by_identifier", None)
    if getter is not None:
        return getter((domain, identifier), entry_id)
    return reg.async_get_device(identifiers={(domain, identifier)})


def devices_with_macs(reg: dr.DeviceRegistry, macs: Iterable[str]) -> list:
    """Every device (any integration) that has one of these MAC connections."""
    conns = {(dr.CONNECTION_NETWORK_MAC, mac) for mac in macs}
    if not conns:
        return []
    getter = getattr(reg, "async_get_devices", None)
    if getter is not None:
        return list(getter(connections=conns))
    return [d for d in reg.devices.values() if d.connections & conns]  # pragma: no cover - old HA


def device_owned_by(device, entry_id: str) -> bool:
    """True when the device belongs to this config entry."""
    owner = getattr(device, "config_entry_id", None)
    if owner is not None:
        return owner == entry_id
    return entry_id in getattr(device, "config_entries", ())  # pragma: no cover - old HA
