"""Custom model fields used across the project."""

from __future__ import annotations

from django.db import models

from .security import EncryptionError, decrypt, encrypt


class EncryptedTextField(models.TextField):
    """A ``TextField`` that transparently encrypts values at rest."""

    prefix = "enc::"

    def _maybe_encrypt(self, value):
        if value is None:
            return value
        if isinstance(value, str) and value.startswith(self.prefix):
            return value
        if value == "":
            return value
        return f"{self.prefix}{encrypt(value)}"

    def _maybe_decrypt(self, value):
        if value is None or value == "":
            return value
        if isinstance(value, str) and value.startswith(self.prefix):
            payload = value[len(self.prefix) :]
            try:
                return decrypt(payload)
            except EncryptionError:
                # اگر داده قدیمی به شکل متن ساده ذخیره شده باشد، آن را برمی‌گردانیم
                return value
        return value

    def from_db_value(self, value, expression, connection):
        return self._maybe_decrypt(value)

    def to_python(self, value):
        return self._maybe_decrypt(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return self._maybe_encrypt(value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self._maybe_encrypt(value)


__all__ = ["EncryptedTextField"]
