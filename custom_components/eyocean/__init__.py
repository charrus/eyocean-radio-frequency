"""EYOCEAN lamp commands over Home Assistant's native RF abstraction."""

import asyncio
from weakref import WeakValueDictionary

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_entity_registry_updated_event
from homeassistant.helpers.typing import ConfigType

from .const import CONF_REMOTE_ID, CONF_REPEATS, CONF_TRANSMITTER, CONF_XOR_KEY, DOMAIN
from .protocol import EyoceanCommand
from .services import async_setup_services

PLATFORMS = [Platform.BUTTON]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register explicit diagnostic actions without sending commands."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Validate stored configuration and set up command entities without transmitting."""
    try:
        EyoceanCommand(
            entry.data[CONF_REMOTE_ID], entry.data[CONF_XOR_KEY], 0x51, entry.data[CONF_REPEATS]
        )
    except (KeyError, ValueError) as err:
        raise ConfigEntryError("Invalid stored EYOCEAN identity or repeat count") from err
    target = entry.data.get(CONF_TRANSMITTER)
    resolved = (
        er.async_resolve_entity_id(er.async_get(hass), target) if isinstance(target, str) else None
    )
    if (
        resolved is None
        or not resolved.startswith("radio_frequency.")
        or er.async_get(hass).async_get(resolved) is None
    ):
        raise ConfigEntryError("RF transmitter was removed; reconfigure the EYOCEAN integration")
    registered = er.async_get(hass).async_get(resolved)
    # Normalize legacy entity-ID references before tracking renames/reloading.
    if target != registered.id:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_TRANSMITTER: registered.id}
        )

    async def async_transmitter_renamed(event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        # The HA 2026.11 consumer tracks a resolved ID, not registry renames.
        # Reload once per entry to replace all six availability subscriptions
        # with the current ID. Setup/reload never sends RF.
        if event.data["action"] == "update" and ATTR_ENTITY_ID in event.data["changes"]:
            await hass.config_entries.async_reload(entry.entry_id)

    entry.async_on_unload(
        async_track_entity_registry_updated_event(hass, resolved, async_transmitter_renamed)
    )
    # Entry runtime data and in-flight presses own the locks. Weak values discard
    # unused transmitter UUIDs without removing a lock still held by a press.
    locks = hass.data.setdefault(DOMAIN, WeakValueDictionary())
    if (lock := locks.get(registered.id)) is None:
        locks[registered.id] = lock = asyncio.Lock()
    entry.runtime_data = lock
    entry.async_on_unload(lambda: setattr(entry, "runtime_data", None))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove buttons and their transmitter subscriptions."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
