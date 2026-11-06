"""Exercise the integration against real HA RF entities, with no radio hardware."""

import asyncio
from types import SimpleNamespace

import pytest
from homeassistant.components.radio_frequency import RadioFrequencyTransmitterEntity
from homeassistant.components.radio_frequency.const import DATA_COMPONENT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry


class TestTransmitter(RadioFrequencyTransmitterEntity):
    __test__ = False
    _attr_unique_id = "test_433_tx"
    _attr_name = "Test 433 TX"

    def __init__(self):
        self.commands = []
        self.fail = False

    @property
    def supported_frequency_ranges(self):
        return [(433_920_000, 433_920_000)]

    async def async_send_command(self, command):
        if self.fail:
            raise HomeAssistantError("Test transmitter failure")
        self.commands.append(command)


@pytest.fixture(autouse=True)
def enable_custom(enable_custom_integrations):
    """Load this checkout as a custom integration."""


@pytest.fixture
async def transmitter(hass):
    assert await async_setup_component(hass, "radio_frequency", {})
    tx = TestTransmitter()
    tx.entity_id = "radio_frequency.test_433_tx"
    await hass.data[DATA_COMPONENT].async_add_entities([tx])
    await hass.async_block_till_done()
    return tx


@pytest.fixture
async def entry(hass, transmitter):
    registry = er.async_get(hass)
    registered = registry.async_get(transmitter.entity_id)
    assert registered is not None
    entry = MockConfigEntry(
        domain="eyocean",
        title="Desk",
        unique_id="BAD1-4E",
        data={
            "name": "Desk",
            "transmitter": registered.id,
            "remote_id": 0xBAD1,
            "xor_key": 0x4E,
            "repeats": 8,
            "swap_night_timer": False,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_buttons_use_native_rf_and_do_not_invent_state(hass, transmitter, entry):
    states = hass.states.async_all("button")
    assert len(states) == 6
    assert hass.states.async_all("light") == []
    assert transmitter.commands == []  # setup must never send RF
    button = next(s for s in states if s.attributes["friendly_name"].endswith("Power toggle"))
    await hass.services.async_call(
        "button", "press", {"entity_id": button.entity_id}, blocking=True
    )
    assert len(transmitter.commands) == 1
    assert transmitter.commands[0].frame == 0xBAD1511F
    assert transmitter.commands[0].repeat_count == 7
    assert hass.states.get(transmitter.entity_id).state != "unknown"


async def test_raw_service_uses_native_transmitter(hass, transmitter, entry):
    timings = [280, -400, 610, -11700]
    assert transmitter.commands == []
    await hass.services.async_call(
        "eyocean",
        "send_raw",
        {"transmitter": entry.data["transmitter"], "timings": timings, "repeats": 8},
        blocking=True,
    )
    assert len(transmitter.commands) == 1
    command = transmitter.commands[0]
    assert command.frequency == 433_920_000
    assert command.get_raw_timings() == timings
    assert command.repeat_count == 7
    assert hass.states.get(transmitter.entity_id).state != "unknown"


async def test_raw_service_refuses_unavailable_transmitter(hass, transmitter, entry):
    transmitter._attr_available = False
    transmitter.async_write_ha_state()
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError, match="unavailable"):
        await hass.services.async_call(
            "eyocean",
            "send_raw",
            {"transmitter": entry.data["transmitter"], "timings": [250, -250]},
            blocking=True,
        )
    assert transmitter.commands == []


@pytest.mark.parametrize("target", ["radio_frequency.missing", "button.desk_power_toggle"])
async def test_raw_service_rejects_invalid_target(hass, transmitter, entry, target):
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "eyocean",
            "send_raw",
            {"transmitter": target, "timings": [250, -250]},
            blocking=True,
        )
    assert transmitter.commands == []


async def test_raw_service_failure_does_not_update_timestamp(hass, transmitter, entry):
    previous = hass.states.get(transmitter.entity_id).state
    transmitter.fail = True
    with pytest.raises(HomeAssistantError, match="Test transmitter failure"):
        await hass.services.async_call(
            "eyocean",
            "send_raw",
            {"transmitter": transmitter.entity_id, "timings": [250, -250]},
            blocking=True,
        )
    assert transmitter.commands == []
    assert hass.states.get(transmitter.entity_id).state == previous


async def test_raw_service_shares_button_lock_after_rename(hass, transmitter, entry, monkeypatch):
    from custom_components.eyocean import services as services_module

    registry = er.async_get(hass)
    registry.async_update_entity(transmitter.entity_id, new_entity_id="radio_frequency.renamed_tx")
    await hass.async_block_till_done()
    sleeping = asyncio.Event()
    release = asyncio.Event()
    delays = []

    async def hold_airtime(delay):
        delays.append(delay)
        sleeping.set()
        await release.wait()

    monkeypatch.setattr(services_module, "asyncio", SimpleNamespace(sleep=hold_airtime))
    raw = asyncio.create_task(
        hass.services.async_call(
            "eyocean",
            "send_raw",
            {"transmitter": entry.data["transmitter"], "timings": [250, -250], "repeats": 2},
            blocking=True,
        )
    )
    button_task = None
    try:
        await asyncio.wait_for(sleeping.wait(), timeout=1)
        assert entry.runtime_data.locked()
        assert len(transmitter.commands) == 1
        assert delays == [0.001]
        button_task = asyncio.create_task(
            hass.services.async_call(
                "button",
                "press",
                {"entity_id": "button.desk_power_toggle"},
                blocking=True,
            )
        )
        await asyncio.sleep(0)
        assert len(transmitter.commands) == 1
    finally:
        release.set()
        await asyncio.gather(raw, *([button_task] if button_task else []))
    assert len(transmitter.commands) == 2
    assert transmitter.commands[1].frame == 0xBAD1511F


async def test_raw_service_rejects_invalid_waveform(hass, transmitter, entry):
    with pytest.raises(HomeAssistantError, match="alternate"):
        await hass.services.async_call(
            "eyocean",
            "send_raw",
            {"transmitter": transmitter.entity_id, "timings": [True, -250]},
            blocking=True,
        )
    assert transmitter.commands == []


async def test_consumer_resolves_uuid_for_both_rf_api_versions(hass, transmitter, entry):
    """The new consumer needs an entity ID, never the stored registry UUID."""
    from custom_components.eyocean.button import COMMAND_BUTTONS, EyoceanButton

    assert entry.data["transmitter"] != transmitter.entity_id
    for definition in COMMAND_BUTTONS:
        button = EyoceanButton(entry, transmitter.entity_id, *definition)
        assert button._rf_transmitter_entity_id == transmitter.entity_id
        assert button._rf_transmitter_entity_id_or_uuid == entry.data["transmitter"]


async def test_legacy_entity_id_is_normalized_before_rename(hass, transmitter, entry):
    """Legacy stored IDs must not break the reload used by the HA 2026.11 API."""
    transmitter_uuid = entry.data["transmitter"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "transmitter": transmitter.entity_id}
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data["transmitter"] == transmitter_uuid
    registry = er.async_get(hass)
    for index in range(2):
        registry.async_update_entity(
            transmitter.entity_id, new_entity_id=f"radio_frequency.legacy_renamed_{index}"
        )
        await hass.async_block_till_done()
        assert len(hass.states.async_all("button")) == 6
        assert all(button.state != "unavailable" for button in hass.states.async_all("button"))
        assert entry.data["transmitter"] == transmitter_uuid
    assert transmitter.commands == []


@pytest.mark.parametrize("use_entity_id", [False, True])
async def test_entries_sharing_transmitter_wait_for_burst_airtime(
    hass, transmitter, entry, monkeypatch, use_entity_id
):
    from custom_components.eyocean import button as button_module

    # A registry rename must not create a separate scheduling identity.
    er.async_get(hass).async_update_entity(
        transmitter.entity_id, new_entity_id="radio_frequency.renamed_tx"
    )
    await hass.async_block_till_done()
    second_entry = MockConfigEntry(
        domain="eyocean",
        title="Second desk",
        unique_id="DCCF-76",
        data={
            **entry.data,
            "name": "Second desk",
            "remote_id": 0xDCCF,
            "xor_key": 0x76,
            "transmitter": transmitter.entity_id if use_entity_id else entry.data["transmitter"],
        },
    )
    second_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second_entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    buttons = [
        next(
            registered.entity_id
            for registered in er.async_entries_for_config_entry(registry, config_entry.entry_id)
            if registered.unique_id.endswith("_power_toggle")
        )
        for config_entry in (entry, second_entry)
    ]
    sleeping = asyncio.Event()
    release_airtime = asyncio.Event()
    delays = []

    async def hold_airtime(delay):
        delays.append(delay)
        sleeping.set()
        await release_airtime.wait()

    # Replace only the integration's sleep, not asyncio used by HA or this test.
    monkeypatch.setattr(button_module, "asyncio", SimpleNamespace(sleep=hold_airtime))
    first = asyncio.create_task(
        hass.services.async_call("button", "press", {"entity_id": buttons[0]}, blocking=True)
    )
    second = None
    try:
        await asyncio.wait_for(sleeping.wait(), timeout=1)
        assert len(transmitter.commands) == 1
        second_started = asyncio.Event()
        original_press = button_module.EyoceanButton.async_press

        async def press_second(button):
            second_started.set()
            await original_press(button)

        monkeypatch.setattr(button_module.EyoceanButton, "async_press", press_second)
        second = asyncio.create_task(
            hass.services.async_call("button", "press", {"entity_id": buttons[1]}, blocking=True)
        )
        # The second press runs until blocked by the lock (or the held sleep).
        await asyncio.wait_for(second_started.wait(), timeout=1)
        assert len(transmitter.commands) == 1
        command = transmitter.commands[0]
        assert delays == [
            sum(abs(t) for t in command.get_raw_timings()) * (command.repeat_count + 1) / 1_000_000
        ]
    finally:
        release_airtime.set()
        await asyncio.gather(first, *([second] if second is not None else []))
    assert [command.frame for command in transmitter.commands] == [0xBAD1511F, 0xDCCF5127]
    assert len(delays) == 2
    transmitter_uuid = entry.data["transmitter"]
    assert list(hass.data["eyocean"]) == [transmitter_uuid]
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert hass.data["eyocean"][transmitter_uuid] is second_entry.runtime_data
    assert await hass.config_entries.async_unload(second_entry.entry_id)
    await hass.async_block_till_done()
    assert not hass.data["eyocean"]


async def test_user_flow_and_no_setup_transmission(hass, transmitter):
    result = await hass.config_entries.flow.async_init("eyocean", context={"source": "user"})
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Desk",
            "transmitter": transmitter.entity_id,
            "remote_id": "0xBAD1",
            "xor_key": "4E",
            "repeats": 8,
            "swap_night_timer": False,
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"]["remote_id"] == 0xBAD1
    assert result["data"]["xor_key"] == 0x4E
    assert result["data"]["transmitter"] == er.async_get(hass).async_get(transmitter.entity_id).id
    await hass.async_block_till_done()
    assert transmitter.commands == []


async def test_transmitter_availability_and_rename(hass, transmitter, entry):
    button = next(
        s
        for s in hass.states.async_all("button")
        if s.attributes["friendly_name"].endswith("Power toggle")
    )
    transmitter._attr_available = False
    transmitter.async_write_ha_state()
    await hass.async_block_till_done()
    assert hass.states.get(button.entity_id).state == "unavailable"
    transmitter._attr_available = True
    transmitter.async_write_ha_state()
    await hass.async_block_till_done()
    assert hass.states.get(button.entity_id).state != "unavailable"
    registry = er.async_get(hass)
    registry.async_update_entity(transmitter.entity_id, new_entity_id="radio_frequency.renamed_tx")
    await hass.async_block_till_done()
    await hass.services.async_call(
        "button", "press", {"entity_id": button.entity_id}, blocking=True
    )
    assert transmitter.commands[-1].frame == 0xBAD1511F


async def test_transmitter_failure_is_not_a_success(hass, transmitter, entry):
    button = next(
        s
        for s in hass.states.async_all("button")
        if s.attributes["friendly_name"].endswith("Power toggle")
    )
    previous = hass.states.get(transmitter.entity_id).state
    transmitter.fail = True
    with pytest.raises(HomeAssistantError, match="Test transmitter failure"):
        await hass.services.async_call(
            "button", "press", {"entity_id": button.entity_id}, blocking=True
        )
    assert transmitter.commands == []
    assert hass.states.get(transmitter.entity_id).state == previous


async def test_swap_night_and_timer_and_unload(hass, transmitter, entry):
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert all(s.state == "unavailable" for s in hass.states.async_all("button"))
    hass.config_entries.async_update_entry(entry, data={**entry.data, "swap_night_timer": True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for suffix, cmd in [("Night light", 0x4D), ("Timer", 0x41)]:
        button = next(
            s
            for s in hass.states.async_all("button")
            if s.attributes["friendly_name"].endswith(suffix)
        )
        await hass.services.async_call(
            "button", "press", {"entity_id": button.entity_id}, blocking=True
        )
        assert (transmitter.commands[-1].frame >> 8) & 0xFF == cmd


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("remote_id", "0000", "invalid_remote_id"),
        ("remote_id", "0x10000", "invalid_remote_id"),
        ("xor_key", "0x100", "invalid_xor_key"),
        ("name", " ", "invalid_name"),
        ("repeats", 1.5, "invalid_repeats"),
    ],
)
async def test_flow_rejects_bad_input(hass, transmitter, field, value, error):
    result = await hass.config_entries.flow.async_init("eyocean", context={"source": "user"})
    data = {
        "name": "Desk",
        "transmitter": transmitter.entity_id,
        "remote_id": "BAD1",
        "xor_key": "4E",
        "repeats": 8,
        "swap_night_timer": False,
    }
    data[field] = value
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["type"] == "form"
    assert result["errors"][field] == error
    assert transmitter.commands == []


async def test_no_transmitters_aborts(hass):
    result = await hass.config_entries.flow.async_init("eyocean", context={"source": "user"})
    assert result["type"] == "abort"
    assert result["reason"] == "no_compatible_transmitters"


async def test_duplicate_remote_rejected(hass, transmitter, entry):
    result = await hass.config_entries.flow.async_init("eyocean", context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Duplicate",
            "transmitter": transmitter.entity_id,
            "remote_id": "BAD1",
            "xor_key": "4E",
            "repeats": 8,
            "swap_night_timer": False,
        },
    )
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


async def test_reconfigure_changes_encoder_without_setup_transmission(hass, transmitter, entry):
    result = await hass.config_entries.flow.async_init(
        "eyocean",
        context={
            "source": "reconfigure",
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Updated desk",
            "transmitter": transmitter.entity_id,
            "remote_id": "DCCF",
            "xor_key": "76",
            "repeats": 1,
            "swap_night_timer": False,
        },
    )
    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert transmitter.commands == []
    assert entry.unique_id == "DCCF-76"
    button = next(
        s
        for s in hass.states.async_all("button")
        if s.attributes["friendly_name"].endswith("Power toggle")
    )
    await hass.services.async_call(
        "button", "press", {"entity_id": button.entity_id}, blocking=True
    )
    assert transmitter.commands[-1].frame == 0xDCCF5127
    assert transmitter.commands[-1].repeat_count == 0


async def test_selector_rejects_unlisted_transmitter(hass, transmitter):
    from homeassistant.data_entry_flow import InvalidData

    result = await hass.config_entries.flow.async_init("eyocean", context={"source": "user"})
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Desk",
                "transmitter": "radio_frequency.missing",
                "remote_id": "BAD1",
                "xor_key": "4E",
                "repeats": 8,
                "swap_night_timer": False,
            },
        )
    assert transmitter.commands == []


async def test_missing_registry_target_refuses_entry_setup(hass, transmitter):
    broken = MockConfigEntry(
        domain="eyocean",
        title="Broken",
        data={
            "name": "Broken",
            "transmitter": "dead_registry_uuid",
            "remote_id": 0xBAD1,
            "xor_key": 0x4E,
            "repeats": 8,
            "swap_night_timer": False,
        },
    )
    broken.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(broken.entry_id)
    await hass.async_block_till_done()
    assert transmitter.commands == []
