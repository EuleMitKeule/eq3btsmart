from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from construct import Construct

from eq3btsmart._adapters import _Eq3AwayTime
from eq3btsmart.exceptions import Eq3InvalidDataException


def test_encode_valid_datetime() -> None:
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45)
    encoded = _Eq3AwayTime.from_datetime(dt)
    expected_bytes = bytes([15, 22, 22, 6])
    assert encoded == expected_bytes


def test_encode_valid_datetime_with_minute() -> None:
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=25)
    encoded = _Eq3AwayTime.from_datetime(dt)
    expected_bytes = bytes([15, 22, 21, 6])
    assert encoded == expected_bytes


def test_decode_valid_bytes() -> None:
    encoded_bytes = bytes([15, 22, 21, 6])
    decoded = _Eq3AwayTime.to_datetime(encoded_bytes)
    expected_datetime = datetime(year=2022, month=6, day=15, hour=10, minute=30)
    assert decoded == expected_datetime


def test_round_trip_consistency() -> None:
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45)
    encoded = _Eq3AwayTime.from_datetime(dt)
    decoded = _Eq3AwayTime.to_datetime(encoded)
    dt_adjusted = dt + timedelta(minutes=15)
    dt_adjusted -= timedelta(minutes=dt_adjusted.minute % 30)
    assert decoded == dt_adjusted


def test_decode_special_case() -> None:
    encoded_bytes = bytes([0x00, 0x00, 0x00, 0x00])
    decoded = _Eq3AwayTime.to_datetime(encoded_bytes)
    expected_datetime = datetime(year=2000, month=1, day=1, hour=0, minute=0)
    assert decoded == expected_datetime


def test_encode_invalid_year() -> None:
    dt = datetime(year=2100, month=6, day=15, hour=10, minute=45)
    with pytest.raises(Eq3InvalidDataException):
        _Eq3AwayTime.from_datetime(dt)


def test_encode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45)
    value = _Eq3AwayTime(subcon)
    encoded = value._encode(dt, MagicMock(), "")
    expected_bytes = bytes([15, 22, 22, 6])
    assert encoded == expected_bytes


def test_decode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    encoded_bytes = bytes([15, 22, 21, 6])
    value = _Eq3AwayTime(subcon)
    decoded = value._decode(encoded_bytes, MagicMock(), "")
    expected_datetime = datetime(year=2022, month=6, day=15, hour=10, minute=30)
    assert decoded == expected_datetime
