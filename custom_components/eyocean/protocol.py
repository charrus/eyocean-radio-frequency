"""EYOCEAN 32-bit fixed-code waveform for 433.92 MHz ASK/OOK remotes.

Reference: https://github.com/bl4ko/eyocean-ha (MIT).
An identity belongs to a remote. It is not derived from the lamp model.
"""

import re

from rf_protocols import ModulationType, RadioFrequencyCommand

FREQUENCY = 433_920_000
COMMANDS = frozenset((0x51, 0x5B, 0x5A, 0x49, 0x4D, 0x41))


def parse_hex(value: str, digits: int) -> int:
    """Parse a bounded hexadecimal UI input, rejecting malformed tokens."""
    if not isinstance(value, str) or not re.fullmatch(
        rf"(?:0[xX])?[0-9a-fA-F]{{1,{digits}}}", value
    ):
        raise ValueError(f"Expected one to {digits} hexadecimal digits")
    return int(value, 16)


class EyoceanCommand(RadioFrequencyCommand):
    """One frame; repeat_count follows rf_protocols' additional-repeat semantics."""

    def __init__(self, remote_id: int, xor_key: int, command: int, repeats: int = 8) -> None:
        for value, low, high in ((remote_id, 1, 0xFFFF), (xor_key, 0, 0xFF), (repeats, 1, 20)):
            if type(value) is not int or not low <= value <= high:
                raise ValueError("Identity or repeat count out of range")
        if type(command) is not int or command not in COMMANDS:
            raise ValueError("Unsupported EYOCEAN command")
        super().__init__(
            frequency=FREQUENCY,
            modulation=ModulationType.OOK,
            repeat_count=repeats - 1,
        )
        self.frame = (remote_id << 16) | (command << 8) | (command ^ xor_key)

    def get_raw_timings(self) -> list[int]:
        """Return a fresh waveform in signed microseconds, MSB first."""
        raw = [250, -6250]
        for bit in range(31, -1, -1):
            raw.extend((750, -250) if self.frame & (1 << bit) else (250, -750))
        return raw
