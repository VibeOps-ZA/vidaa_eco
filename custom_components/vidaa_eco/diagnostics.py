"""Diagnostics support for Hisense TV.

Diagnostics files are often attached to public GitHub issues, so everything
that identifies a home network or a TV is redacted: IP addresses, every MAC
address (hardware, Ethernet, Wi-Fi, Wake-on-LAN target, auth placeholder),
certificate paths and the TV's own name.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import VidaaTVConfigEntry

TO_REDACT = {
    # config entry data / options
    "host",
    "mac",
    "hw_mac",
    "mac_ethernet",
    "mac_wifi",
    "wol_mac",
    "device_id",
    "certfile",
    "keyfile",
    # TV device info (getdeviceinfo) and the cached copy
    "ip",
    "name",
    "tv_name",
    "network_type",
    "eth0",
    "wlan0",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: VidaaTVConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    tv = runtime_data.tv

    # Live device info, asked through the coordinator so it never overlaps a
    # poll (pyvidaa replies are not matched to their request).
    device_info = None
    try:
        device_info = await coordinator.async_get_device_info(timeout=5)
    except Exception:  # noqa: BLE001 - diagnostics must never fail on this
        pass

    return {
        "config_entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "coordinator": {
            "data": coordinator.data,
            "device_data": async_redact_data(coordinator.device_data, TO_REDACT),
            "available": coordinator.available,
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
            # What auto power-off currently thinks, and where its traffic
            # reading comes from - the first things to look at when it
            # switches a TV off (or never does).
            "auto_off_enabled": getattr(coordinator, "auto_off_enabled", None),
            "auto_off_delay_min": getattr(coordinator, "auto_off_delay_min", None),
            "eco_state": coordinator.eco_state,
            "throughput": getattr(coordinator, "throughput", None),
        },
        "tv_connection": {
            "connected": tv.is_connected if tv else False,
            "device_info": async_redact_data(device_info, TO_REDACT)
            if isinstance(device_info, dict)
            else None,
        },
    }
