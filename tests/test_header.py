import pytest

from tobicloud.header import Header, decode_header, encode_header


def test_header_round_trip():
    header = Header(alias="docs", encrypted=True, length=3, skipped=[1, 4])

    encoded = encode_header(header)

    assert len(encoded) <= 512
    assert decode_header(encoded) == header


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-base64",
        "e30",
        "eyJhIjoxLCJlIjp0cnVlLCJsIjoxLCJzIjpbXX0",
        "eyJhIjpudWxsLCJlIjoiZmFsc2UiLCJsIjoxLCJzIjpbXX0",
        "eyJhIjpudWxsLCJlIjpmYWxzZSwibCI6dHJ1ZSwicyI6W119",
        "eyJhIjpudWxsLCJlIjpmYWxzZSwibCI6MSwicyI6W3RydWVdfQ",
    ],
)
def test_invalid_headers_are_rejected(value):
    with pytest.raises(ValueError):
        decode_header(value)
