from unittest.mock import MagicMock

import pytest
from construct import Construct

from eq3btsmart._adapters import _Eq3Temperature
from eq3btsmart.const import EQ3_OFF_TEMP, EQ3_ON_TEMP
from eq3btsmart.exceptions import Eq3InvalidDataException


def test_encode_valid_temperature() -> None:
    temperature = 22.0
    encoded = _Eq3Temperature.encode(temperature)
    assert encoded == 44


def test_decode_valid_int() -> None:
    encoded_int = 44
    decoded = _Eq3Temperature.decode(encoded_int)
    assert decoded == 22.0


def test_round_trip_consistency() -> None:
    temperature = 22.0
    encoded = _Eq3Temperature.encode(temperature)
    decoded = _Eq3Temperature.decode(encoded)
    assert decoded == temperature


def test_encode_temperature_out_of_range_low() -> None:
    temperature = EQ3_OFF_TEMP - 0.1
    with pytest.raises(Eq3InvalidDataException):
        _Eq3Temperature.encode(temperature)


def test_encode_temperature_out_of_range_high() -> None:
    temperature = EQ3_ON_TEMP + 0.1
    with pytest.raises(Eq3InvalidDataException):
        _Eq3Temperature.encode(temperature)


def test_encode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    temperature = 22.0
    value = _Eq3Temperature(subcon)
    encoded = value._encode(temperature, MagicMock(), "")
    assert encoded == 44


def test_decode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    encoded = 44
    value = _Eq3Temperature(subcon)
    decoded = value._decode(encoded, MagicMock(), "")
    assert decoded == 22.0
