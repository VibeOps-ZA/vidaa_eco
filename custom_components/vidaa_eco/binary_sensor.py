"""HDMI-signal binary sensor for VIDAA Eco.

Surfaces the TV's own `is_signal` flag (present only on the `sourceswitch`
statetype) so automations - and the auto-off logic - can tell whether a live
external source is actually feeding the panel. This is the field the upstream
integration receives but never exposed.

States: "Signal received" while an external input is live, "No signal" while
on an input with nothing attached or on any non-input source (app, live TV,
launcher), and unavailable only while the TV itself is off.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([VidaaSignalSensor(coordinator, entry)])


class VidaaSignalSensor(CoordinatorEntity, BinarySensorEntity):
    """True while a live HDMI/external source is feeding the TV."""

    _attr_has_entity_name = True
    _attr_translation_key = "hdmi_signal"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:hdmi-port"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        did = entry.data.get(CONF_DEVICE_ID)
        self._attr_unique_id = f"{did or entry.entry_id}_hdmi_signal"

    @property
    def device_info(self) -> DeviceInfo:
        did = self._entry.data.get(CONF_DEVICE_ID) or self._entry.entry_id
        return DeviceInfo(identifiers={(DOMAIN, did)})

    @property
    def available(self) -> bool:
        # Only meaningful while the TV is on; an off TV has no inputs to report.
        data = self.coordinator.data or {}
        return bool(data.get("is_on"))

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        if data.get("statetype") != "sourceswitch":
            return False
        return bool(data.get("is_signal"))

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "source": data.get("source") if data.get("statetype") == "sourceswitch" else None,
            "statetype": data.get("statetype"),
        }
