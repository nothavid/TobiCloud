"""Local file loading, encoding, decoding, and writing."""

from __future__ import annotations

from pathlib import Path

from .crypto import decrypt, encrypt
from .encoding import base64_decode_without_padding, base64_encode_without_padding


def load_file_as_payload(path: Path, password: str | None = None) -> str:
    data = path.read_bytes()
    if password is not None:
        data = encrypt(data, password)
    return base64_encode_without_padding(data)


def decode_payload(payload: str, password: str | None = None) -> bytes:
    data = base64_decode_without_padding(payload)
    if password is not None:
        data = decrypt(data, password)
    return data


def write_file(path: Path, data: bytes) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
