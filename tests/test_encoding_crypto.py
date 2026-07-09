from tobicloud.files import decode_payload
from tobicloud.crypto import encrypt
from tobicloud.encoding import base64_encode_without_padding


def test_base64_payload_round_trip_without_encryption():
    payload = base64_encode_without_padding(b"hello cloud")

    assert payload == "aGVsbG8gY2xvdWQ"
    assert decode_payload(payload) == b"hello cloud"


def test_encrypted_payload_round_trip():
    encrypted = encrypt(b"secret bytes", "pw")
    payload = base64_encode_without_padding(encrypted)

    assert "=" not in payload
    assert decode_payload(payload, "pw") == b"secret bytes"
