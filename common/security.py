"""Security helpers such as encryption utilities."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from importlib import import_module
from importlib.util import find_spec
from typing import TYPE_CHECKING, Tuple

from django.conf import settings

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    from cryptography.fernet import Fernet as _Fernet, InvalidToken as _InvalidToken


class EncryptionError(Exception):
    """Raised when encrypting or decrypting data fails."""


@lru_cache(maxsize=1)
def _load_crypto() -> Tuple["_Fernet", "_InvalidToken"]:
    """Lazily import :mod:`cryptography.fernet` and cache the classes."""

    if find_spec("cryptography.fernet") is None:
        raise EncryptionError(
            "cryptography package is required for encryption features. "
            "Install it with `pip install cryptography`."
        )
    module = import_module("cryptography.fernet")
    return module.Fernet, module.InvalidToken


@lru_cache(maxsize=1)
def _get_fernet() -> "_Fernet":
    Fernet, _ = _load_crypto()
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
    _, InvalidToken = _load_crypto()
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - the caller handles gracefully
        raise EncryptionError("Invalid encryption token") from exc


__all__ = ["EncryptionError", "encrypt", "decrypt"]
