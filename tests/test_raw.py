"""Bounds for explicitly requested raw RF diagnostics."""

import pytest

from custom_components.eyocean.services import RawCommand


@pytest.mark.parametrize(
    "timings,repeats",
    [
        ([], 1),
        ([250], 1),
        ([250, 0], 1),
        ([-250, 250], 1),
        ([250, 250], 1),
        ([True, -250], 1),
        ([250.5, -250], 1),
        (["250", -250], 1),
        ([500001, -250], 1),
        ([250, -500001], 1),
        ([250, -250] * 2049, 1),
        ([500000, -500000], 6),
        ([250, -250], True),
        ([250, -250], 0),
        ([250, -250], 21),
        ([250, -250], 1.5),
    ],
)
def test_raw_rejects_unsafe_bursts(timings, repeats):
    with pytest.raises(ValueError):
        RawCommand(timings, repeats)


def test_raw_timings_are_copied():
    source = [250, -250]
    command = RawCommand(source, 20)
    source[0] = 999
    command.get_raw_timings()[0] = 123
    assert command.get_raw_timings() == [250, -250]
    assert command.repeat_count == 19
