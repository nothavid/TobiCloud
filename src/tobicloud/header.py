"""Header encoding and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .encoding import base64_decode_without_padding, base64_encode_without_padding


@dataclass(frozen=True)
class Header:
    alias: str | None
    encrypted: bool
    length: int
    skipped: list[int]


def encode_header(header: Header) -> str:
    raw = json.dumps(
        {
            "a": header.alias,
            "e": header.encrypted,
            "l": header.length,
            "s": header.skipped,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return base64_encode_without_padding(raw)


def decode_header(value: str) -> Header:
    try:
        data = json.loads(base64_decode_without_padding(value).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("Invalid header encoding") from exc

    if not isinstance(data, dict):
        raise ValueError("Header is not a JSON object")

    required = {"a", "e", "l", "s"}
    if not required.issubset(data):
        raise ValueError("Header is missing required fields")

    alias = data["a"]
    encrypted = data["e"]
    length = data["l"]
    skipped = data["s"]

    if alias is not None and not isinstance(alias, str):
        raise ValueError("Header alias must be a string or null")
    if not isinstance(encrypted, bool):
        raise ValueError("Header encryption flag must be boolean")
    if not isinstance(length, int) or isinstance(length, bool) or length < 0:
        raise ValueError("Header length must be a non-negative integer")
    if not isinstance(skipped, list) or not all(_is_non_negative_int(item) for item in skipped):
        raise ValueError("Header skipped list must contain non-negative integers")

    return Header(alias=alias, encrypted=encrypted, length=length, skipped=skipped)


def is_valid_header(value: str) -> bool:
    try:
        decode_header(value)
    except ValueError:
        return False
    return True


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
