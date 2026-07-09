"""Base64 and hashing helpers."""

from __future__ import annotations

import base64
import binascii
import hashlib


def base64_encode_without_padding(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii").rstrip("=")


def base64_decode_without_padding(value: str) -> bytes:
    padding_length = (-len(value)) % 4
    padded = value + ("=" * padding_length)
    try:
        return base64.b64decode(padded.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise ValueError("Invalid base64 value") from exc


def sha256_hex(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()
