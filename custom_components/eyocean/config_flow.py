"""UI setup and reconfiguration; no radio command is sent during either flow."""

from typing import Any

import probatio
from homeassistant.components.radio_frequency import async_get_transmitters
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from rf_protocols import ModulationType

from .const import CONF_REMOTE_ID, CONF_REPEATS, CONF_SWAP, CONF_TRANSMITTER, CONF_XOR_KEY, DOMAIN
from .protocol import FREQUENCY, EyoceanCommand, parse_hex


class EyoceanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure a remote identity and an existing compatible RF transmitter."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_form("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_form("reconfigure", user_input)

    async def _async_form(self, step: str, user_input: dict[str, Any] | None) -> ConfigFlowResult:
        try:
            transmitters = async_get_transmitters(self.hass, FREQUENCY, ModulationType.OOK)
        except HomeAssistantError:
            return self.async_abort(reason="no_compatible_transmitters")
        if not transmitters:
            return self.async_abort(reason="no_compatible_transmitters")

        entry = self._get_reconfigure_entry() if step == "reconfigure" else None
        defaults = dict(entry.data) if entry else {}
        registry = er.async_get(self.hass)
        if entry:
            defaults[CONF_REMOTE_ID] = f"0x{entry.data[CONF_REMOTE_ID]:04X}"
            defaults[CONF_XOR_KEY] = f"0x{entry.data[CONF_XOR_KEY]:02X}"
            defaults[CONF_TRANSMITTER] = er.async_resolve_entity_id(
                registry, entry.data[CONF_TRANSMITTER]
            )
        errors: dict[str, str] = {}
        if user_input is not None:
            defaults.update(user_input)
            remote_id = key = 0
            try:
                remote_id = parse_hex(user_input[CONF_REMOTE_ID], 4)
                if remote_id == 0:
                    raise ValueError("Remote address cannot be zero")
            except ValueError, KeyError:
                errors[CONF_REMOTE_ID] = "invalid_remote_id"
            try:
                key = parse_hex(user_input[CONF_XOR_KEY], 2)
            except ValueError, KeyError:
                errors[CONF_XOR_KEY] = "invalid_xor_key"
            repeats = user_input.get(CONF_REPEATS, 8)
            try:
                if isinstance(repeats, bool) or int(repeats) != repeats:
                    raise ValueError("Repeat count must be an integer")
                repeats = int(repeats)
                EyoceanCommand(1, 0, 0x51, repeats)
            except ValueError, TypeError, OverflowError:
                errors[CONF_REPEATS] = "invalid_repeats"
            selected = user_input.get(CONF_TRANSMITTER)
            transmitter = registry.async_get(selected) if isinstance(selected, str) else None
            if selected not in transmitters or transmitter is None:
                errors[CONF_TRANSMITTER] = "invalid_transmitter"
            name = user_input.get(CONF_NAME, "").strip()
            if not name:
                errors[CONF_NAME] = "invalid_name"
            if not errors:
                identity = f"{remote_id:04X}-{key:02X}"
                if any(
                    e.unique_id == identity and (entry is None or e.entry_id != entry.entry_id)
                    for e in self._async_current_entries()
                ):
                    return self.async_abort(reason="already_configured")
                data = {
                    CONF_NAME: name,
                    CONF_TRANSMITTER: transmitter.id,
                    CONF_REMOTE_ID: remote_id,
                    CONF_XOR_KEY: key,
                    CONF_REPEATS: repeats,
                    CONF_SWAP: user_input.get(CONF_SWAP, False),
                }
                if entry:
                    return self.async_update_reload_and_abort(
                        entry,
                        unique_id=identity,
                        title=name,
                        data=data,
                    )
                await self.async_set_unique_id(identity)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=name, data=data)

        schema = probatio.Schema(
            {
                probatio.Required(
                    CONF_NAME, default=defaults.get(CONF_NAME, "EYOCEAN Desk Lamp")
                ): str,
                probatio.Required(
                    CONF_TRANSMITTER,
                    **(
                        {"default": defaults[CONF_TRANSMITTER]}
                        if defaults.get(CONF_TRANSMITTER)
                        else {}
                    ),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(include_entities=transmitters)
                ),
                probatio.Required(
                    CONF_REMOTE_ID,
                    **({"default": defaults[CONF_REMOTE_ID]} if CONF_REMOTE_ID in defaults else {}),
                ): str,
                probatio.Required(
                    CONF_XOR_KEY,
                    **({"default": defaults[CONF_XOR_KEY]} if CONF_XOR_KEY in defaults else {}),
                ): str,
                probatio.Required(
                    CONF_REPEATS, default=defaults.get(CONF_REPEATS, 8)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=20,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                probatio.Required(CONF_SWAP, default=defaults.get(CONF_SWAP, False)): bool,
            }
        )
        return self.async_show_form(step_id=step, data_schema=schema, errors=errors)
