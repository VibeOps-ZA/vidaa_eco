"""Remote-control and app-launch buttons for VIDAA Eco.

One button entity per practical remote key and per common app, so a media
dashboard can be built from plain button cards without scripts.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID


@dataclass(frozen=True)
class VidaaButton:
    key: str          # unique-id suffix
    name: str
    icon: str
    tv_key: str | None = None   # remote key to send, or
    app: str | None = None      # app to launch (TV's own app name)


BUTTONS: tuple[VidaaButton, ...] = (
    # Navigation
    VidaaButton("key_up", "Up", "mdi:chevron-up", tv_key="KEY_UP"),
    VidaaButton("key_down", "Down", "mdi:chevron-down", tv_key="KEY_DOWN"),
    VidaaButton("key_left", "Left", "mdi:chevron-left", tv_key="KEY_LEFT"),
    VidaaButton("key_right", "Right", "mdi:chevron-right", tv_key="KEY_RIGHT"),
    VidaaButton("key_ok", "OK", "mdi:checkbox-blank-circle-outline", tv_key="KEY_OK"),
    VidaaButton("key_back", "Back", "mdi:arrow-u-left-top", tv_key="KEY_RETURNS"),
    VidaaButton("key_home", "Home", "mdi:home", tv_key="KEY_HOME"),
    VidaaButton("key_menu", "Menu", "mdi:menu", tv_key="KEY_MENU"),
    VidaaButton("key_exit", "Exit", "mdi:exit-to-app", tv_key="KEY_EXIT"),
    VidaaButton("key_info", "Info", "mdi:information-outline", tv_key="KEY_INFO"),
    # Playback
    VidaaButton("key_play", "Play", "mdi:play", tv_key="KEY_PLAY"),
    VidaaButton("key_pause", "Pause", "mdi:pause", tv_key="KEY_PAUSE"),
    VidaaButton("key_stop", "Stop", "mdi:stop", tv_key="KEY_STOP"),
    VidaaButton("key_rewind", "Rewind", "mdi:rewind", tv_key="KEY_BACK"),
    VidaaButton("key_fast_forward", "Fast forward", "mdi:fast-forward", tv_key="KEY_FORWARDS"),
    VidaaButton("key_subtitle", "Subtitles", "mdi:subtitles-outline", tv_key="KEY_SUBTITLE"),
    # Volume / channel
    VidaaButton("key_mute", "Mute", "mdi:volume-mute", tv_key="KEY_MUTE"),
    VidaaButton("key_volume_up", "Volume up", "mdi:volume-plus", tv_key="KEY_VOLUMEUP"),
    VidaaButton("key_volume_down", "Volume down", "mdi:volume-minus", tv_key="KEY_VOLUMEDOWN"),
    VidaaButton("key_channel_up", "Channel up", "mdi:arrow-up-bold-box-outline", tv_key="KEY_CHANNELUP"),
    VidaaButton("key_channel_down", "Channel down", "mdi:arrow-down-bold-box-outline", tv_key="KEY_CHANNELDOWN"),
    # Colour keys
    VidaaButton("key_red", "Red", "mdi:square-rounded", tv_key="KEY_RED"),
    VidaaButton("key_green", "Green", "mdi:square-rounded", tv_key="KEY_GREEN"),
    VidaaButton("key_yellow", "Yellow", "mdi:square-rounded", tv_key="KEY_YELLOW"),
    VidaaButton("key_blue", "Blue", "mdi:square-rounded", tv_key="KEY_BLUE"),
    # Apps - launched by the TV's own app name, as the media player does.
    VidaaButton("app_plex", "Plex", "mdi:plex", app="Plex"),
    VidaaButton("app_youtube", "YouTube", "mdi:youtube", app="YouTube"),
    VidaaButton("app_netflix", "Netflix", "mdi:netflix", app="Netflix"),
    VidaaButton("app_prime_video", "Prime Video", "mdi:filmstrip-box", app="Prime Video"),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(VidaaKeyButton(coordinator, entry, desc) for desc in BUTTONS)

    # One button per physical input the TV reports (TV, HDMI1, HDMI2, AV...).
    # The list comes from the TV's source list, remembered on the entry, so the
    # buttons exist after a restart even while the TV is off; inputs the TV
    # reports later are added as they appear.
    known: set[str] = set()

    @callback
    def _add_inputs() -> None:
        new = []
        for item in coordinator.inputs:
            name = item.get("sourcename") or item.get("sourceid")
            if not name or name.lower() in known:
                continue
            known.add(name.lower())
            new.append(VidaaInputButton(coordinator, entry, item))
        if new:
            async_add_entities(new)

    _add_inputs()
    coordinator.add_input_listener(_add_inputs)


class VidaaKeyButton(CoordinatorEntity, ButtonEntity):
    """Press a remote key or launch an app on the TV."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, desc: VidaaButton) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._desc = desc
        did = entry.data.get(CONF_DEVICE_ID)
        self._attr_unique_id = f"{did or entry.entry_id}_{desc.key}"
        self._attr_name = desc.name
        self._attr_icon = desc.icon

    @property
    def device_info(self) -> DeviceInfo:
        did = self._entry.data.get(CONF_DEVICE_ID) or self._entry.entry_id
        return DeviceInfo(identifiers={(DOMAIN, did)})

    @property
    def available(self) -> bool:
        # A sleeping TV has no MQTT broker to receive the key.
        return bool((self.coordinator.data or {}).get("is_on"))

    async def async_press(self) -> None:
        if self._desc.app:
            await self.coordinator.async_launch_app(self._desc.app)
        else:
            await self.coordinator.async_send_key(self._desc.tv_key)


class VidaaInputButton(CoordinatorEntity, ButtonEntity):
    """Switch the TV to one of its physical inputs."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:video-input-hdmi"

    def __init__(self, coordinator, entry, item: dict) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._sourcename = item.get("sourcename") or item.get("sourceid")
        did = entry.data.get(CONF_DEVICE_ID)
        slug = "".join(c if c.isalnum() else "_" for c in self._sourcename.lower())
        self._attr_unique_id = f"{did or entry.entry_id}_input_{slug}"
        self._attr_name = self._sourcename
        if self._sourcename.upper() == "TV":
            self._attr_name = "TV input"
            self._attr_icon = "mdi:television-classic"
        elif self._sourcename.upper().startswith("AV"):
            self._attr_icon = "mdi:video-input-component"
        label = item.get("displayname")
        self._attr_extra_state_attributes = {
            "sourceid": item.get("sourceid"),
            "label_on_tv": label if label and label != self._sourcename else None,
        }

    @property
    def device_info(self) -> DeviceInfo:
        did = self._entry.data.get(CONF_DEVICE_ID) or self._entry.entry_id
        return DeviceInfo(identifiers={(DOMAIN, did)})

    @property
    def available(self) -> bool:
        return bool((self.coordinator.data or {}).get("is_on"))

    async def async_press(self) -> None:
        await self.coordinator.async_select_source(self._sourcename)
