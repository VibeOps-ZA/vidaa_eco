"""Adjustable auto-off grace delay for VIDAA Eco.

This is the ONLY timer the user sees. It starts counting *after* the TV has
already been confirmed idle for the fixed internal detection window, so the real
unattended time before power-off is (detection window + this value).
"""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID, DEFAULT_AUTO_OFF_DELAY


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([VidaaAutoOffDelay(coordinator, entry)])


class VidaaAutoOffDelay(CoordinatorEntity, RestoreEntity, NumberEntity):
    _attr_has_entity_name = True
    _attr_name = "Auto-off delay"
    _attr_native_min_value = 1
    _attr_native_max_value = 180
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer-cog-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        did = entry.data.get(CONF_DEVICE_ID)
        self._attr_unique_id = f"{did or entry.entry_id}_auto_off_delay"
        self._attr_native_value = float(DEFAULT_AUTO_OFF_DELAY)
        coordinator.auto_off_delay_min = DEFAULT_AUTO_OFF_DELAY

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
        if last and last.state not in (None, "unknown", "unavailable"):
            try:
                v = float(last.state)
                self._attr_native_value = v
                self.coordinator.auto_off_delay_min = int(v)
            except ValueError:
                pass

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.coordinator.auto_off_delay_min = int(value)
        self.async_write_ha_state()
