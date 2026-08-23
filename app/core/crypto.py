"""PII field encryption — AES-256-GCM.

Used to encrypt customer phone/email and generated message content at rest.
The key comes from ``PII_ENCRYPTION_KEY`` (a urlsafe-base64 string encoding >=32 bytes).

Storage format: base64( nonce[12] || ciphertext || tag ).

In development, if no key is configured, values pass through in plaintext with a
one-time warning — so the app still boots without secrets. Never run prod without a key.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_NONCE_BYTES = 12
_PREFIX = "gcm:"  # marks an encrypted value, so we never double-encrypt/decrypt


def _load_key() -> bytes | None:
    raw = settings.pii_encryption_key
    if not raw:
        return None
    # Accept urlsafe-base64 or raw text; derive exactly 32 bytes.
    try:
        key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    except Exception:  # noqa: BLE001
        key = raw.encode()
    if len(key) < 32:
        key = key.ljust(32, b"0")
    return key[:32]


_KEY = _load_key()
_warned = False


def _warn_plaintext() -> None:
    global _warned
    if not _warned:
        log.warning(
            "crypto.no_key",
            msg="PII_ENCRYPTION_KEY unset — storing PII in plaintext (dev only)",
        )
        _warned = True


def encrypt_field(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    if _KEY is None:
        _warn_plaintext()
        return plaintext
    if plaintext.startswith(_PREFIX):
        return plaintext  # already encrypted
    nonce = os.urandom(_NONCE_BYTES)
    ct = AESGCM(_KEY).encrypt(nonce, plaintext.encode(), None)
    return _PREFIX + base64.b64encode(nonce + ct).decode()


def decrypt_field(stored: str | None) -> str | None:
    if stored is None:
        return None
    if _KEY is None or not stored.startswith(_PREFIX):
        return stored
    blob = base64.b64decode(stored[len(_PREFIX) :])
    nonce, ct = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    return AESGCM(_KEY).decrypt(nonce, ct, None).decode()


def hash_identifier(value: str | None) -> str | None:
    """Stable SHA-256 of a normalized phone/email — used for DNC lookups.

    Storing the hash (not the raw value) lets us match DNC entries without keeping
    another copy of plaintext PII.
    """
    if not value:
        return None
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


class EncryptedString(TypeDecorator):
    """SQLAlchemy column type that transparently encrypts on write / decrypts on read."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001
        return encrypt_field(value)

    def process_result_value(self, value, dialect):  # noqa: ANN001
        return decrypt_field(value)
