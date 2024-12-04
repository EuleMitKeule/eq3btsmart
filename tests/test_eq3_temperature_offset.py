from unittest.mock import MagicMock

import pytest
from construct import Construct

from eq3btsmart._adapters import _Eq3TemperatureOffset
from eq3btsmart.const import EQ3_MAX_OFFSET, EQ3_MIN_OFFSET
from eq3btsmart.exceptions import Eq3InvalidDataException


def test_encode_valid_temperature_offset() -> None:
    offset = 1.0
    encoded = _Eq3TemperatureOffset.encode(offset)
    assert encoded == 9


def test_decode_valid_int() -> None:
    encoded_int = 9
    decoded = _Eq3TemperatureOffset.decode(encoded_int)
    assert decoded == 1.0


def test_round_trip_consistency() -> None:
    offset = 1.0
    encoded = _Eq3TemperatureOffset.encode(offset)
    decoded = _Eq3TemperatureOffset.decode(encoded)
    assert decoded == offset


def test_encode_temperature_offset_out_of_range_low() -> None:
    offset = EQ3_MIN_OFFSET - 0.1
    with pytest.raises(Eq3InvalidDataException):
        _Eq3TemperatureOffset.encode(offset)


def test_encode_temperature_offset_out_of_range_high() -> None:
    offset = EQ3_MAX_OFFSET + 0.1
    with pytest.raises(Eq3InvalidDataException):
        _Eq3TemperatureOffset.encode(offset)


def test_encode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    offset = 1.0
    value = _Eq3TemperatureOffset(subcon)
    encoded = value._encode(offset, MagicMock(), "")
    assert encoded == 9


def test_decode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    encoded = 9
    value = _Eq3TemperatureOffset(subcon)
    decoded = value._decode(encoded, MagicMock(), "")
    assert decoded == 1.0
