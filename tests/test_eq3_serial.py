from unittest.mock import MagicMock

from construct import Construct

from eq3btsmart._adapters import _Eq3Serial


def test_encode_valid_string() -> None:
    string = "example"
    encoded = _Eq3Serial.encode(string)
    assert encoded == bytes([ord(char) + 0x30 for char in string])


def test_decode_valid_bytes() -> None:
    encoded_bytes = bytes([ord(char) + 0x30 for char in "example"])
    decoded = _Eq3Serial.decode(encoded_bytes)
    assert decoded == "example"


def test_round_trip_consistency() -> None:
    string = "example"
    encoded = _Eq3Serial.encode(string)
    decoded = _Eq3Serial.decode(encoded)
    assert decoded == string


def test_encode_empty_string() -> None:
    string = ""
    encoded = _Eq3Serial.encode(string)
    assert encoded == b""


def test_decode_empty_bytes() -> None:
    encoded_bytes = b""
    decoded = _Eq3Serial.decode(encoded_bytes)
    assert decoded == ""


def test_encode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    string = "example"
    value = _Eq3Serial(subcon)
    encoded = value._encode(string, MagicMock(), "")
    assert encoded == bytes([ord(char) + 0x30 for char in string])


def test_decode() -> None:
    subcon = MagicMock(spec=Construct)
    subcon.flagbuildnone = False
    encoded = bytes([ord(char) + 0x30 for char in "example"])
    value = _Eq3Serial(subcon)
    decoded = value._decode(encoded, MagicMock(), "")
    assert decoded == "example"
