from eq3btsmart.adapter.eq3_serial import Eq3Serial


def test_encode_valid_string():
    string = "example"
    encoded = Eq3Serial._encode(string)
    assert encoded == bytes([ord(char) + 0x30 for char in string])


def test_decode_valid_bytes():
    encoded_bytes = bytes([ord(char) + 0x30 for char in "example"])
    decoded = Eq3Serial._decode(encoded_bytes)
    assert decoded == "example"


def test_round_trip_consistency():
    string = "example"
    encoded = Eq3Serial._encode(string)
    decoded = Eq3Serial._decode(encoded)
    assert decoded == string


def test_encode_empty_string():
    string = ""
    encoded = Eq3Serial._encode(string)
    assert encoded == b""


def test_decode_empty_bytes():
    encoded_bytes = b""
    decoded = Eq3Serial._decode(encoded_bytes)
    assert decoded == ""
