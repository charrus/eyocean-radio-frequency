"""Explicit raw 433.92 MHz OOK diagnostics through Home Assistant RF entities."""

import asyncio
from weakref import WeakValueDictionary

import probatio
from homeassistant.components.radio_frequency.helpers import async_send_command
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_register_admin_service
from rf_protocols import ModulationType, RadioFrequencyCommand

from .const import DOMAIN
from .protocol import FREQUENCY


class RawCommand(RadioFrequencyCommand):
    """A captured waveform, with total repeats converted to additional repeats."""

    def __init__(self, timings: list[int], repeats: int) -> None:
        if type(repeats) is not int or not 1 <= repeats <= 20:
            raise ValueError("Repeats must be an integer from 1 to 20")
        if not isinstance(timings, list) or not 2 <= len(timings) <= 4096 or len(timings) % 2:
            raise ValueError("Provide 2 to 4096 alternating mark/space timings, ending in a space")
        for index, timing in enumerate(timings):
            if (
                type(timing) is not int
                or not 1 <= abs(timing) <= 500_000
                or (timing > 0) != (index % 2 == 0)
            ):
                raise ValueError(
                    "Timings must alternate positive/negative integers up to 500000 us"
                )
        if sum(abs(timing) for timing in timings) * repeats > 5_000_000:
            raise ValueError("Total encoded burst duration must not exceed five seconds")
        super().__init__(
            frequency=FREQUENCY, modulation=ModulationType.OOK, repeat_count=repeats - 1
        )
        self._timings = list(timings)

    def get_raw_timings(self) -> list[int]:
        """Return an independent copy of the signed-microsecond waveform."""
        return list(self._timings)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register an administrator-only action; registering never transmits."""
    locks = hass.data.setdefault(DOMAIN, WeakValueDictionary())

    async def async_send_raw(call: ServiceCall) -> None:
        """Serialize an explicit raw burst with this integration's lamp buttons."""
        try:
            command = RawCommand(call.data["timings"], call.data["repeats"])
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        registry = er.async_get(hass)
        entity_id = er.async_resolve_entity_id(registry, call.data["transmitter"])
        registered = registry.async_get(entity_id) if entity_id else None
        if registered is None or registered.domain != "radio_frequency":
            raise ServiceValidationError("Select a registered radio_frequency transmitter")
        if (lock := locks.get(registered.id)) is None:
            locks[registered.id] = lock = asyncio.Lock()
        async with lock:
            # Recheck after waiting: the adapter may have gone offline in the queue.
            current_id = er.async_resolve_entity_id(registry, registered.id)
            state = hass.states.get(current_id) if current_id else None
            if state is None or state.state == STATE_UNAVAILABLE:
                raise ServiceValidationError("RF transmitter is unavailable")
            await async_send_command(hass, registered.id, command, context=call.context)
            airtime = sum(abs(t) for t in command.get_raw_timings())
            await asyncio.sleep(airtime * (command.repeat_count + 1) / 1_000_000)

    async_register_admin_service(
        hass,
        DOMAIN,
        "send_raw",
        async_send_raw,
        schema=probatio.Schema(
            {
                probatio.Required("transmitter"): str,
                probatio.Required("timings"): list,
                probatio.Optional("repeats", default=1): int,
            }
        ),
    )
