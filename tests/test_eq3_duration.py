from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from construct import Construct

from eq3btsmart._adapters import _Eq3Duration
from eq3btsmart.exceptions import Eq3InvalidDataException


def test_encode_valid_timedelta() -> None:
    td = timedelta(minutes=25)
    encoded = _Eq3Duration.encode(td)
    assert encoded == 5


def test_decode_valid_int() -> None:
    encoded_int = 5
    decoded = _Eq3Duration.decode(encoded_int)
    assert decoded == timedelta(minutes=25)


def test_round_trip_consistency() -> None:
    td = timedelta(minutes=25)
    encoded = _Eq3Duration.encode(td)
    decoded = _Eq3Duration.decode(encoded)
    assert decoded == td


def test_encode_invalid_timedelta_negative() -> None:
    td = timedelta(minutes=-5)
    with pytest.raises(Eq3InvalidDataException):
        _Eq3Duration.encode(td)


def test_encode_invalid_timedelta_exceed() -> None:
    td = timedelta(minutes=65)
    with pytest.raises(Eq3InvalidDataException):
        _Eq3Duration.encode(td)


def test_encode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    td = timedelta(minutes=25)
    value = _Eq3Duration(subcon)
    encoded = value._encode(td, MagicMock(), "")
    assert encoded == 5


def test_decode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    encoded = 5
    value = _Eq3Duration(subcon)
    decoded = value._decode(encoded, MagicMock(), "")
    assert decoded == timedelta(minutes=25)
