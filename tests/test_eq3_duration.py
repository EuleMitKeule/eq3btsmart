from datetime import timedelta

import pytest

from eq3btsmart.adapter.eq3_duration import Eq3Duration
from eq3btsmart.exceptions import Eq3InvalidDataException


def test_encode_valid_timedelta() -> None:
    td = timedelta(minutes=25)
    encoded = Eq3Duration.encode(td)
    assert encoded == 5


def test_decode_valid_int() -> None:
    encoded_int = 5
    decoded = Eq3Duration.decode(encoded_int)
    assert decoded == timedelta(minutes=25)


def test_round_trip_consistency() -> None:
    td = timedelta(minutes=25)
    encoded = Eq3Duration.encode(td)
    decoded = Eq3Duration.decode(encoded)
    assert decoded == td


def test_encode_invalid_timedelta_negative() -> None:
    td = timedelta(minutes=-5)
    with pytest.raises(Eq3InvalidDataException):
        Eq3Duration.encode(td)


def test_encode_invalid_timedelta_exceed() -> None:
    td = timedelta(minutes=65)
    with pytest.raises(Eq3InvalidDataException):
        Eq3Duration.encode(td)
