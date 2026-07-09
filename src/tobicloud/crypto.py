"""Password-based encryption helpers."""

from __future__ import annotations

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 200_000
KEY_LENGTH = 32
NONCE_LENGTH = 12
MAGIC = b"TC1"
FIXED_SALT = b"tobicloud-fixed-salt-v1"


def derive_key(password: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=FIXED_SALT,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt(data: bytes, password: str) -> bytes:
    nonce = os.urandom(NONCE_LENGTH)
    ciphertext = AESGCM(derive_key(password)).encrypt(nonce, data, None)
    return MAGIC + nonce + ciphertext


def decrypt(data: bytes, password: str) -> bytes:
    if not data.startswith(MAGIC):
        raise ValueError("Encrypted payload has an unknown format")

    nonce_start = len(MAGIC)
    nonce_end = nonce_start + NONCE_LENGTH
    nonce = data[nonce_start:nonce_end]
    ciphertext = data[nonce_end:]

    if len(nonce) != NONCE_LENGTH or not ciphertext:
        raise ValueError("Encrypted payload is incomplete")

    try:
        return AESGCM(derive_key(password)).decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise ValueError("Unable to decrypt payload; the password may be incorrect") from exc
