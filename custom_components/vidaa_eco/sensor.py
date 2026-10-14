"""VIDAA Eco state and activity sensors.

Two plain sensors that make the TV's situation readable at a glance:

- ``<TV> Auto-off status``: what the auto power-off logic is doing, as text -
  Off / Auto-off disabled / In use / HDMI in use – no timer / Idle – checking /
  Powering off in N min.
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
    ECO_STATE_ACTIVE,
    ECO_STATE_COUNTDOWN,
    ECO_STATE_DISABLED,
    ECO_STATE_HDMI,
    ECO_STATE_IDLE,
    ECO_STATE_OFF,
)

ACTIVITY_OFF = "Off"
ACTIVITY_INACTIVE = "Inactive"

STATUS_TEXT = {
    ECO_STATE_OFF: "Off",
    ECO_STATE_DISABLED: "Auto-off disabled",
    ECO_STATE_ACTIVE: "In use",
    ECO_STATE_HDMI: "HDMI in use – no timer",
    ECO_STATE_IDLE: "Idle – checking",
}


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
    """Auto-off status: what the auto power-off logic is doing, in plain words.

    The state is human-readable text ("Powering off in 7 min"); the stable
    machine value for automations is the ``status`` attribute
    (off / disabled / active / hdmi / idle / countdown).
    """

    _attr_translation_key = "auto_off_status"
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator, entry) -> None:
        # unique_id suffix stays "eco_state" so the existing entity is kept.
        super().__init__(coordinator, entry, "eco_state")

    @property
    def native_value(self) -> str:
        eco = self.coordinator.eco_state or {}
        status = eco.get("state", ECO_STATE_OFF)
        if status == ECO_STATE_COUNTDOWN:
            return f"Powering off in {eco.get('minutes_remaining', 0)} min"
        if status == ECO_STATE_HDMI:
            source = (self.coordinator.data or {}).get("source") or "Input"
            return f"{source} in use – no timer"
        if status == ECO_STATE_IDLE and eco.get("no_signal"):
            return "No signal – checking"
        return STATUS_TEXT.get(status, status)

    @property
    def extra_state_attributes(self) -> dict:
        eco = self.coordinator.eco_state or {}
        data = self.coordinator.data or {}
        return {
            "status": eco.get("state", ECO_STATE_OFF),
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
            "signal": _signal_text(data),
            "signal_detail": data.get("signal_detail"),
            "app": data.get("app"),
            "source": data.get("source"),
            "channel_name": data.get("channel_name"),
            "channel_number": data.get("channel_number"),
        }


def _signal_text(data: dict) -> str | None:
    """'yes' / 'no' while on an external input, else None."""
    if not data.get("is_on") or data.get("statetype") != "sourceswitch":
        return None
    signal = data.get("is_signal")
    if signal is None:
        return "unknown"
    return "yes" if signal else "no"


def _activity(data: dict) -> str:
    """Reduce the coordinator's state to one human-readable line."""
    if not data.get("is_on"):
        return ACTIVITY_OFF
    statetype = data.get("statetype")
    if statetype == "app":
        return data.get("app") or data.get("source") or "App"
    if statetype == "sourceswitch":
        source = data.get("source") or "Input"
        return f"{source} – no signal" if data.get("is_signal") is False else source
    if statetype == "livetv":
        channel = data.get("channel_name")
        return f"TV: {channel}" if channel else "Live TV"
    # remote_launcher, remote_setting, anything else while on -> nothing
    # a viewer would miss; mirrors what the idle logic treats as idle.
    return ACTIVITY_INACTIVE
