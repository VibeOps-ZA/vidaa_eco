"""Play a media URL on a VIDAA TV through its built-in DLNA renderer.

VIDAA TVs advertise a standard UPnP/DLNA *MediaRenderer* (AVTransport,
RenderingControl, ConnectionManager) on the local network via SSDP. Its
description URL includes a port that **changes on every boot** (seen 18400 and
38400), so it is never hard-coded: the newest location announced by the TV over
SSDP is used (see ``VidaaTVDataUpdateCoordinator.async_ssdp_seen``), falling
back to Home Assistant's own SSDP cache.

Uses ``async_upnp_client``, which ships with Home Assistant (the SSDP and DLNA
integrations depend on it), so there is no extra requirement.
"""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

MEDIA_RENDERER_ST = "urn:schemas-upnp-org:device:MediaRenderer:1"


def location_host(location: str | None) -> str | None:
    """Host part of an SSDP LOCATION URL."""
    if not location:
        return None
    try:
        return urlparse(location).hostname
    except ValueError:
        return None


async def async_find_location(hass: HomeAssistant, host: str) -> str | None:
    """Look the TV's renderer description URL up in Home Assistant's SSDP cache."""
    try:
        from homeassistant.components import ssdp

        for info in await ssdp.async_get_discovery_info_by_st(hass, MEDIA_RENDERER_ST):
            if location_host(info.ssdp_location) == host:
                return info.ssdp_location
    except Exception as err:  # noqa: BLE001 - SSDP not loaded / not ready
        _LOGGER.debug("SSDP lookup for %s failed: %s", host, err)
    return None


async def async_play_url(
    hass: HomeAssistant,
    location: str,
    url: str,
    title: str,
    mime_type: str | None = None,
) -> None:
    """Load ``url`` on the renderer at ``location`` and start playback."""
    from async_upnp_client.aiohttp import AiohttpSessionRequester
    from async_upnp_client.client_factory import UpnpFactory
    from async_upnp_client.profiles.dlna import DmrDevice

    session = async_get_clientsession(hass, verify_ssl=False)
    requester = AiohttpSessionRequester(session, with_sleep=True, timeout=10)
    try:
        device = await UpnpFactory(requester, non_strict=True).async_create_device(location)
        dmr = DmrDevice(device, event_handler=None)
        meta = await dmr.construct_play_media_metadata(
            media_url=url,
            media_title=title,
            override_mime_type=mime_type,
        )
        # Stop whatever the renderer is doing first; many TVs refuse a new URI
        # while a previous one is still loaded.
        try:
            await dmr.async_stop()
        except Exception:  # noqa: BLE001 - nothing playing is fine
            pass
        await dmr.async_set_transport_uri(url, title, meta)
        await dmr.async_wait_for_can_play(max_wait_time=10)
        last_err: Exception | None = None
        for _ in range(3):
            try:
                await dmr.async_play()
                return
            except Exception as err:  # noqa: BLE001 - retried below
                last_err = err
                await asyncio.sleep(1)
        raise HomeAssistantError(f"The TV did not start playback: {last_err}")
    except HomeAssistantError:
        raise
    except Exception as err:
        raise HomeAssistantError(f"DLNA playback on the TV failed: {err}") from err
