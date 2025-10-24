"""Security helpers such as encryption utilities."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class EncryptionError(Exception):
    """Raised when encrypting or decrypting data fails."""


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    secret = settings.SECRET_KEY.encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt(text: str) -> str:
    """Encrypt *text* returning a URL safe base64 string."""

    if text is None:
        raise ValueError("`text` must be a string, not None")
    fernet = _get_fernet()
    return fernet.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """Decrypt *token* returning the original string."""

    if token is None:
        raise ValueError("`token` must be a string, not None")
    fernet = _get_fernet()
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - the caller handles gracefully
        raise EncryptionError("Invalid encryption token") from exc


__all__ = ["EncryptionError", "encrypt", "decrypt"]
