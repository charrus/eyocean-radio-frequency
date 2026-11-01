"""Protocol checks against public EYOCEAN example vectors (no hardware)."""

import pytest

from custom_components.eyocean.protocol import EyoceanCommand, parse_hex


def test_published_power_frame_and_timings():
    command = EyoceanCommand(0xBAD1, 0x4E, 0x51)
    assert command.frame == 0xBAD1511F
    assert command.frequency == 433_920_000
    assert command.repeat_count == 7  # rf_protocols counts ADDITIONAL transmissions
    raw = command.get_raw_timings()
    assert len(raw) == 66
    assert raw[:2] == [250, -6250]
    decoded = 0
    for high, low in zip(raw[2::2], raw[3::2], strict=True):
        assert (high, low) in ((250, -750), (750, -250))
        decoded = decoded << 1 | (high == 750)
    assert decoded == 0xBAD1511F
    raw.clear()
    assert len(command.get_raw_timings()) == 66


@pytest.mark.parametrize(
    "remote_id,key,cmd,frame",
    [
        (0xDCCF, 0x76, 0x51, 0xDCCF5127),
        (0xBAD1, 0x4E, 0x5B, 0xBAD15B15),
        (0xBAD1, 0x4E, 0x5A, 0xBAD15A14),
    ],
)
def test_known_frames(remote_id, key, cmd, frame):
    assert EyoceanCommand(remote_id, key, cmd).frame == frame


@pytest.mark.parametrize(
    "remote_id,key,cmd,repeats",
    [
        (0, 0, 0x51, 8),
        (65536, 0, 0x51, 8),
        (True, 0, 0x51, 8),
        (1, -1, 0x51, 8),
        (1, 256, 0x51, 8),
        (1, 1, 0xFF, 8),
        (1, 1, 0x51, 0),
        (1, 1, 0x51, 21),
        (1, 1, 0x51, 1.5),
    ],
)
def test_reject_bad_values(remote_id, key, cmd, repeats):
    with pytest.raises(ValueError):
        EyoceanCommand(remote_id, key, cmd, repeats)


def test_repeat_total_one_and_zero_xor_key():
    command = EyoceanCommand(1, 0, 0x51, 1)
    assert command.repeat_count == 0
    assert command.frame == 0x00015151


@pytest.mark.parametrize(
    "text,digits,expected", [("0xBAD1", 4, 0xBAD1), ("bad1", 4, 0xBAD1), ("00", 2, 0)]
)
def test_hex_input(text, digits, expected):
    assert parse_hex(text, digits) == expected


@pytest.mark.parametrize("text", ["0x", "-1", "0x10000", " BAD1", "BAD1 ", "xyz", "12345", 1234])
def test_invalid_hex_input(text):
    with pytest.raises(ValueError):
        parse_hex(text, 4)
