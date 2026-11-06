"""Stateless command buttons: the remote has no absolute-state feedback."""

import asyncio

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.components.radio_frequency import RadioFrequencyTransmitterConsumerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_REMOTE_ID, CONF_REPEATS, CONF_SWAP, CONF_TRANSMITTER, CONF_XOR_KEY, DOMAIN
from .protocol import EyoceanCommand

COMMAND_BUTTONS = (
    ("power_toggle", "Power toggle", 0x51, "mdi:desk-lamp"),
    ("brightness_cycle", "Brightness cycle", 0x5B, "mdi:brightness-6"),
    ("color_temperature_cycle", "Color temperature cycle", 0x5A, "mdi:thermometer"),
    ("reading_mode", "Reading mode", 0x49, "mdi:book-open-variant"),
    ("night_light", "Night light", 0x41, "mdi:weather-night"),
    ("timer", "Timer", 0x4D, "mdi:timer-outline"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Create buttons for this lamp's remote identity."""
    transmitter_entity_id = er.async_validate_entity_id(
        er.async_get(hass), entry.data[CONF_TRANSMITTER]
    )
    async_add_entities(
        EyoceanButton(entry, transmitter_entity_id, *definition) for definition in COMMAND_BUTTONS
    )


class EyoceanButton(RadioFrequencyTransmitterConsumerEntity, ButtonEntity):
    """A button backed by a native RF transmitter, with availability/rename tracking."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        transmitter_entity_id: str,
        key: str,
        name: str,
        command: int,
        icon: str,
    ) -> None:
        self.entity_description = ButtonEntityDescription(key=key, name=name, icon=icon)
        self._entry = entry
        self._command = command
        if entry.data.get(CONF_SWAP, False) and key in ("night_light", "timer"):
            self._command = 0x4D if key == "night_light" else 0x41
        self._rf_transmitter_entity_id_or_uuid = entry.data[CONF_TRANSMITTER]
        # HA 2026.11 requires a resolved entity ID for availability tracking.
        # Keep the UUID-based attribute for the HA 2026.10 consumer as well.
        self._rf_transmitter_entity_id = transmitter_entity_id
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="EYOCEAN",
            model="433.92 MHz RF desk lamp",
        )

    async def async_press(self) -> None:
        """Encode the configured remote identity and send through radio_frequency."""
        command = EyoceanCommand(
            self._entry.data[CONF_REMOTE_ID],
            self._entry.data[CONF_XOR_KEY],
            self._command,
            self._entry.data[CONF_REPEATS],
        )
        async with self._entry.runtime_data:
            await self._send_command(command)
            # The native ESPHome send call returns before optical/RF completion.
            # Space successive local button requests by the encoded burst airtime.
            airtime = sum(abs(t) for t in command.get_raw_timings())
            await asyncio.sleep(airtime * (command.repeat_count + 1) / 1_000_000)
