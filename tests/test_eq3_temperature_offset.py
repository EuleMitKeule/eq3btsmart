import pytest

from eq3btsmart.adapter.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.const import EQ3BT_MAX_OFFSET, EQ3BT_MIN_OFFSET
from eq3btsmart.exceptions import Eq3InvalidDataException


def test_encode_valid_temperature_offset() -> None:
    offset = 1.0
    encoded = Eq3TemperatureOffset.encode(offset)
    assert encoded == 9


def test_decode_valid_int() -> None:
    encoded_int = 9
    decoded = Eq3TemperatureOffset.decode(encoded_int)
    assert decoded == 1.0


def test_round_trip_consistency() -> None:
    offset = 1.0
    encoded = Eq3TemperatureOffset.encode(offset)
    decoded = Eq3TemperatureOffset.decode(encoded)
    assert decoded == offset


def test_encode_temperature_offset_out_of_range_low() -> None:
    offset = EQ3BT_MIN_OFFSET - 0.1
    with pytest.raises(Eq3InvalidDataException):
        Eq3TemperatureOffset.encode(offset)


def test_encode_temperature_offset_out_of_range_high() -> None:
    offset = EQ3BT_MAX_OFFSET + 0.1
    with pytest.raises(Eq3InvalidDataException):
        Eq3TemperatureOffset.encode(offset)
