from datetime import time
from unittest.mock import MagicMock

from construct import Construct

from eq3btsmart._adapters import _Eq3ScheduleTime


def test_encode_valid_time() -> None:
    t = time(hour=13, minute=30)
    encoded = _Eq3ScheduleTime.encode(t)
    assert encoded == 81


def test_decode_valid_int() -> None:
    encoded_int = 81
    decoded = _Eq3ScheduleTime.decode(encoded_int)
    assert decoded == time(hour=13, minute=30)


def test_round_trip_consistency() -> None:
    t = time(hour=13, minute=30)
    encoded = _Eq3ScheduleTime.encode(t)
    decoded = _Eq3ScheduleTime.decode(encoded)
    assert decoded == t


def test_encode_edge_case() -> None:
    t = time(hour=23, minute=59)
    encoded = _Eq3ScheduleTime.encode(t)
    assert encoded == 143


def test_decode_edge_case() -> None:
    encoded_int = 143
    decoded = _Eq3ScheduleTime.decode(encoded_int)
    assert decoded == time(hour=23, minute=50)


def test_encode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    t = time(hour=13, minute=30)
    value = _Eq3ScheduleTime(subcon)
    encoded = value._encode(t, MagicMock(), "")
    assert encoded == 81


def test_decode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    encoded = 81
    value = _Eq3ScheduleTime(subcon)
    decoded = value._decode(encoded, MagicMock(), "")
    assert decoded == time(hour=13, minute=30)
