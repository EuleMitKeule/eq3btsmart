from datetime import datetime
from unittest.mock import MagicMock

import pytest
from construct import Construct

from eq3btsmart._adapters import _Eq3Time
from eq3btsmart.exceptions import Eq3InvalidDataException


def test_encode_valid_datetime() -> None:
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45, second=30)
    encoded = _Eq3Time.encode(dt)
    assert encoded == bytes([22, 6, 15, 10, 45, 30])


def test_decode_valid_bytes() -> None:
    encoded_bytes = bytes([22, 6, 15, 10, 45, 30])
    decoded = _Eq3Time.decode(encoded_bytes)
    assert decoded == datetime(
        year=2022, month=6, day=15, hour=10, minute=45, second=30
    )


def test_round_trip_consistency() -> None:
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45, second=30)
    encoded = _Eq3Time.encode(dt)
    decoded = _Eq3Time.decode(encoded)
    assert decoded == dt


def test_decode_invalid_bytes_length() -> None:
    encoded_bytes = bytes([22, 6, 15, 10, 45])
    with pytest.raises(Eq3InvalidDataException):
        _Eq3Time.decode(encoded_bytes)


def test_encode_future_date() -> None:
    dt = datetime(year=2122, month=6, day=15, hour=10, minute=45, second=30)
    encoded = _Eq3Time.encode(dt)
    assert encoded == bytes([22, 6, 15, 10, 45, 30])


def test_encode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45, second=30)
    value = _Eq3Time(subcon)
    encoded = value._encode(dt, MagicMock(), "")
    assert encoded == bytes([22, 6, 15, 10, 45, 30])


def test_decode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    encoded = bytes([22, 6, 15, 10, 45, 30])
    value = _Eq3Time(subcon)
    decoded = value._decode(encoded, MagicMock(), "")
    assert decoded == datetime(
        year=2022, month=6, day=15, hour=10, minute=45, second=30
    )
