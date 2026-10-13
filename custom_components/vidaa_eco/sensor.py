"""VIDAA Eco state and activity sensors.

Two plain sensors that make the TV's situation readable at a glance:

- ``<TV> Eco state``: what the auto power-off logic currently thinks -
  ``off`` / ``active`` / ``idle`` (silent confirm window) / ``countdown``
  (the user's grace delay is running) / ``disabled`` (switch off).
- ``<TV> Activity``: what is on screen - an app name, an input, a channel,
  ``Inactive`` at the launcher/settings, ``Off`` when the TV is off.
"""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    ECO_STATES,
    ECO_STATE_OFF,
)

ACTIVITY_OFF = "Off"
ACTIVITY_INACTIVE = "Inactive"


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([
        VidaaEcoStateSensor(coordinator, entry),
        VidaaActivitySensor(coordinator, entry),
    ])


class _VidaaSensorBase(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, suffix: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        did = entry.data.get(CONF_DEVICE_ID)
        self._attr_unique_id = f"{did or entry.entry_id}_{suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        did = self._entry.data.get(CONF_DEVICE_ID) or self._entry.entry_id
        return DeviceInfo(identifiers={(DOMAIN, did)})

    @property
    def available(self) -> bool:
        # An unreachable TV is a power state, not a sensor failure: these
        # sensors report "off" rather than dropping to unavailable.
        return True


class VidaaEcoStateSensor(_VidaaSensorBase):
    """What the auto power-off logic currently thinks of the TV."""

    _attr_translation_key = "eco_state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(ECO_STATES)
    _attr_icon = "mdi:television-ambient-light"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "eco_state")

    @property
    def native_value(self) -> str:
        return (self.coordinator.eco_state or {}).get("state", ECO_STATE_OFF)

    @property
    def extra_state_attributes(self) -> dict:
        eco = self.coordinator.eco_state or {}
        data = self.coordinator.data or {}
        return {
            "statetype": data.get("statetype"),
            "activity": _activity(data),
            "idle_since": eco.get("idle_since"),
            "idle_minutes": eco.get("idle_minutes"),
            "minutes_remaining": eco.get("minutes_remaining"),
            "power_off_at": eco.get("power_off_at"),
        }


class VidaaActivitySensor(_VidaaSensorBase):
    """What the TV is showing: app, input, channel, Inactive or Off."""

    _attr_translation_key = "activity"
    _attr_icon = "mdi:television-play"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "activity")

    @property
    def native_value(self) -> str:
        return _activity(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "statetype": data.get("statetype"),
            "app": data.get("app"),
            "source": data.get("source"),
            "channel_name": data.get("channel_name"),
            "channel_number": data.get("channel_number"),
        }


def _activity(data: dict) -> str:
    """Reduce the coordinator's state to one human-readable line."""
    if not data.get("is_on"):
        return ACTIVITY_OFF
    statetype = data.get("statetype")
    if statetype == "app":
        return data.get("app") or data.get("source") or "App"
    if statetype == "sourceswitch":
        return data.get("source") or "Input"
    if statetype == "livetv":
        channel = data.get("channel_name")
        return f"TV: {channel}" if channel else "Live TV"
    # remote_launcher, remote_setting, anything else while on -> nothing
    # a viewer would miss; mirrors what the idle logic treats as idle.
    return ACTIVITY_INACTIVE
