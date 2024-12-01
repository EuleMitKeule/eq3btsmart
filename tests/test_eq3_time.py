from datetime import datetime

import pytest

from eq3btsmart.adapter.eq3_time import Eq3Time
from eq3btsmart.exceptions import Eq3InvalidDataException


def test_encode_valid_datetime() -> None:
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45, second=30)
    encoded = Eq3Time.encode(dt)
    assert encoded == bytes([22, 6, 15, 10, 45, 30])


def test_decode_valid_bytes() -> None:
    encoded_bytes = bytes([22, 6, 15, 10, 45, 30])
    decoded = Eq3Time.decode(encoded_bytes)
    assert decoded == datetime(
        year=2022, month=6, day=15, hour=10, minute=45, second=30
    )


def test_round_trip_consistency() -> None:
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45, second=30)
    encoded = Eq3Time.encode(dt)
    decoded = Eq3Time.decode(encoded)
    assert decoded == dt


def test_decode_invalid_bytes_length() -> None:
    encoded_bytes = bytes([22, 6, 15, 10, 45])
    with pytest.raises(Eq3InvalidDataException):
        Eq3Time.decode(encoded_bytes)


def test_encode_future_date() -> None:
    dt = datetime(year=2122, month=6, day=15, hour=10, minute=45, second=30)
    encoded = Eq3Time.encode(dt)
    assert encoded == bytes([22, 6, 15, 10, 45, 30])
