"""Enable/disable the VIDAA Eco automatic power-off for a TV.

Off by default: the integration never powers a TV off unless the owner opts in,
so people who only want the remote/buttons never have to set anything up.

Turning it on requires a network-throughput source (picked in the options, or
auto-detected from a router integration): without one an open app can never be
told apart from a playing one. See throughput.py and the README.
"""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID, DEFAULT_AUTO_OFF_ENABLED, DOCS_THROUGHPUT_URL


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([VidaaAutoOffSwitch(coordinator, entry)])


class VidaaAutoOffSwitch(CoordinatorEntity, RestoreEntity, SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Auto power-off"
    _attr_icon = "mdi:power-sleep"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        did = entry.data.get(CONF_DEVICE_ID)
        self._attr_unique_id = f"{did or entry.entry_id}_auto_off"
        self._attr_is_on = DEFAULT_AUTO_OFF_ENABLED
        coordinator.auto_off_enabled = DEFAULT_AUTO_OFF_ENABLED

    @property
    def device_info(self) -> DeviceInfo:
        did = self._entry.data.get(CONF_DEVICE_ID) or self._entry.entry_id
        return DeviceInfo(identifiers={(DOMAIN, did)})

    @property
    def available(self) -> bool:
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            self._attr_is_on = last.state == "on"
        self.coordinator.auto_off_enabled = bool(self._attr_is_on)

    async def async_turn_on(self, **kwargs) -> None:
        sources, _mode = self.coordinator.throughput_sources()
        if not sources:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="throughput_required",
                translation_placeholders={"tv": self._entry.title, "url": DOCS_THROUGHPUT_URL},
            )
        self._attr_is_on = True
        self.coordinator.auto_off_enabled = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self.coordinator.auto_off_enabled = False
        self.async_write_ha_state()
