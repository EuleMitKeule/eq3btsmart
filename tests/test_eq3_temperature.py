import pytest

from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.const import EQ3BT_OFF_TEMP, EQ3BT_ON_TEMP
from eq3btsmart.exceptions import Eq3InvalidDataException


def test_encode_valid_temperature() -> None:
    temperature = 22.0
    encoded = Eq3Temperature.encode(temperature)
    assert encoded == 44


def test_decode_valid_int() -> None:
    encoded_int = 44
    decoded = Eq3Temperature.decode(encoded_int)
    assert decoded == 22.0


def test_round_trip_consistency() -> None:
    temperature = 22.0
    encoded = Eq3Temperature.encode(temperature)
    decoded = Eq3Temperature.decode(encoded)
    assert decoded == temperature


def test_encode_temperature_out_of_range_low() -> None:
    temperature = EQ3BT_OFF_TEMP - 0.1
    with pytest.raises(Eq3InvalidDataException):
        Eq3Temperature.encode(temperature)


def test_encode_temperature_out_of_range_high() -> None:
    temperature = EQ3BT_ON_TEMP + 0.1
    with pytest.raises(Eq3InvalidDataException):
        Eq3Temperature.encode(temperature)
