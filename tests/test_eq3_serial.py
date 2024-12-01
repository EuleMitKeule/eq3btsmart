from eq3btsmart.adapter.eq3_serial import Eq3Serial


def test_encode_valid_string() -> None:
    string = "example"
    encoded = Eq3Serial.encode(string)
    assert encoded == bytes([ord(char) + 0x30 for char in string])


def test_decode_valid_bytes() -> None:
    encoded_bytes = bytes([ord(char) + 0x30 for char in "example"])
    decoded = Eq3Serial.decode(encoded_bytes)
    assert decoded == "example"


def test_round_trip_consistency() -> None:
    string = "example"
    encoded = Eq3Serial.encode(string)
    decoded = Eq3Serial.decode(encoded)
    assert decoded == string


def test_encode_empty_string() -> None:
    string = ""
    encoded = Eq3Serial.encode(string)
    assert encoded == b""


def test_decode_empty_bytes() -> None:
    encoded_bytes = b""
    decoded = Eq3Serial.decode(encoded_bytes)
    assert decoded == ""
