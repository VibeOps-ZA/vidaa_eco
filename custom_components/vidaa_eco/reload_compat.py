"""How VIDAA Eco reloads itself after a settings change, on old and new Home Assistant.

Why this exists
---------------
Two things change a TV's config entry while it is running:

1. **The options dialog** (Settings -> Devices & services -> VIDAA Eco ->
   Configure). Those changes only take effect after a reload.
2. **Discovery** finding the TV at a new IP address. The config flow then
   stores the new address (``_abort_if_unique_id_configured(updates=...)``)
   and Home Assistant reloads the entry so it reconnects to the new address.

Up to eco.9 an *update listener* did the reloading for (1). From Home
Assistant 2026.12 an entry that has an update listener is no longer reloaded
by Home Assistant for (2) - the listener is expected to do it - and ours
deliberately ignored data-only changes, so a TV that changed address would
not reconnect until Home Assistant restarted.

The supported way (Home Assistant 2025.8+) is ``OptionsFlowWithReload``: the
options flow reloads the entry itself, and the integration registers NO
update listener, so Home Assistant keeps reloading for (2). Home Assistant
refuses to combine the two, so the listener is only used on versions that
do not have ``OptionsFlowWithReload``.

No Home Assistant imports here, so it can be unit-tested directly.
"""
from __future__ import annotations

from typing import Any

RELOADING_OPTIONS_FLOW = "OptionsFlowWithReload"


def has_reloading_options_flow(config_entries_module: Any) -> bool:
    """True when this Home Assistant has OptionsFlowWithReload (2025.8+)."""
    return hasattr(config_entries_module, RELOADING_OPTIONS_FLOW)


def options_flow_base(config_entries_module: Any) -> type:
    """The class VIDAA Eco's options flow derives from."""
    if has_reloading_options_flow(config_entries_module):
        return getattr(config_entries_module, RELOADING_OPTIONS_FLOW)
    return config_entries_module.OptionsFlow


def needs_update_listener(config_entries_module: Any) -> bool:
    """Only older Home Assistant needs our own listener to apply options."""
    return not has_reloading_options_flow(config_entries_module)
