"""Boot real Home Assistant and verify RF buttons without pytest fixtures or hardware."""

import asyncio
import importlib.metadata
import sys
import tempfile
from pathlib import Path

# Support direct execution without installing this custom integration as a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant import auth, bootstrap, config_entries, loader  # noqa: E402
from homeassistant.components.radio_frequency import RadioFrequencyTransmitterEntity  # noqa: E402
from homeassistant.components.radio_frequency.const import DATA_COMPONENT  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers import entity_registry as er  # noqa: E402


class MemoryTransmitter(RadioFrequencyTransmitterEntity):
    """Use native RF dispatch, but never access radio hardware."""

    _attr_unique_id = "compatibility_test_transmitter"
    _attr_name = "Compatibility transmitter"

    def __init__(self):
        self.commands = []

    @property
    def supported_frequency_ranges(self):
        return [(433_920_000, 433_920_000)]

    async def async_send_command(self, command):
        self.commands.append(command)


async def check(config_dir):
    """Verify setup, service dispatch, renames, availability and unload."""
    hass = HomeAssistant(config_dir)
    loader.async_setup(hass)
    hass.config.skip_pip = True
    try:
        from homeassistant.setup import async_setup_component

        # Initialize only core helpers and RF dependencies. Do not start an HTTP
        # listener, discover real devices, or load the user's HA configuration.
        hass.config_entries = config_entries.ConfigEntries(hass, {})
        assert await bootstrap.async_load_base_functionality(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [], [])
        assert await async_setup_component(hass, "homeassistant", {})
        assert await async_setup_component(hass, "radio_frequency", {})
        transmitter = MemoryTransmitter()
        transmitter.entity_id = "radio_frequency.compatibility_transmitter"
        await hass.data[DATA_COMPONENT].async_add_entities([transmitter])
        await hass.async_block_till_done(wait_background_tasks=True)
        result = await hass.config_entries.flow.async_init("eyocean", context={"source": "user"})
        assert result["type"] == "form", result
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Compatibility desk",
                "transmitter": transmitter.entity_id,
                "remote_id": "BAD1",
                "xor_key": "4E",
                "repeats": 8,
                "swap_night_timer": False,
            },
        )
        assert result["type"] == "create_entry", result
        entry = result["result"]
        await hass.async_block_till_done(wait_background_tasks=True)
        registry = er.async_get(hass)
        assert entry.data["transmitter"] == registry.async_get(transmitter.entity_id).id
        buttons = hass.states.async_all("button")
        assert len(buttons) == 6, (
            f"Expected 6 RF buttons, found {len(buttons)}; "
            f"entry state={entry.state}, reason={entry.reason}"
        )
        assert all(button.state != "unavailable" for button in buttons)
        assert not transmitter.commands, "Setup must not transmit"
        button_id = next(
            button.entity_id
            for button in buttons
            if button.attributes["friendly_name"].endswith("Power toggle")
        )
        await hass.services.async_call("button", "press", {"entity_id": button_id}, blocking=True)
        assert len(transmitter.commands) == 1
        assert transmitter.commands[-1].frame == 0xBAD1511F
        assert transmitter.commands[-1].repeat_count == 7
        for index in range(2):
            registry.async_update_entity(
                transmitter.entity_id,
                new_entity_id=f"radio_frequency.renamed_compatibility_transmitter_{index}",
            )
            await hass.async_block_till_done(wait_background_tasks=True)
            assert hass.states.get(button_id).state != "unavailable"
            await hass.services.async_call(
                "button", "press", {"entity_id": button_id}, blocking=True
            )
            assert len(transmitter.commands) == index + 2
        transmitter._attr_available = False
        transmitter.async_write_ha_state()
        await hass.async_block_till_done(wait_background_tasks=True)
        assert all(button.state == "unavailable" for button in hass.states.async_all("button"))
        transmitter._attr_available = True
        transmitter.async_write_ha_state()
        await hass.async_block_till_done(wait_background_tasks=True)
        assert all(button.state != "unavailable" for button in hass.states.async_all("button"))
        sent = len(transmitter.commands)
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert all(button.state == "unavailable" for button in hass.states.async_all("button"))
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert len(hass.states.async_all("button")) == 6
        assert all(button.state != "unavailable" for button in hass.states.async_all("button"))
        assert len(transmitter.commands) == sent, "Reload must not transmit"
        print(
            f"PASS Home Assistant {importlib.metadata.version('homeassistant')}: "
            "6 buttons, UUID storage, encoded dispatch, repeat count, two renames, "
            "availability recovery, unload/reload, no setup/reload RF"
        )
    finally:
        await hass.async_stop(force=True)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="eyocean-ha-compat-") as config_dir:
        asyncio.run(check(config_dir))
