"""Utility helpers for interacting with SMS providers."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict, Optional

from django.conf import settings

__all__ = [
    "SMSConfigurationError",
    "BaseSMSProvider",
    "ConsoleSMSProvider",
    "KavenegarSMSProvider",
    "get_sms_provider",
    "really_send_sms",
]

logger = logging.getLogger(__name__)


class SMSConfigurationError(RuntimeError):
    """Raised when the SMS subsystem is misconfigured."""


class BaseSMSProvider:
    """Base class for SMS providers."""

    def send(self, phone_number: str, message: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class ConsoleSMSProvider(BaseSMSProvider):
    """A provider that simply prints messages to stdout."""

    def send(self, phone_number: str, message: str) -> None:
        print(f"Sending SMS to {phone_number}: {message}")


class KavenegarSMSProvider(BaseSMSProvider):
    """Adapter for the Kavenegar SMS gateway."""

    def __init__(self, api_key: str, sender: Optional[str] = None) -> None:
        try:
            from kavenegar import APIException, HTTPException, KavenegarAPI  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised via configuration error tests
            raise SMSConfigurationError(
                "The 'kavenegar' package is required for the Kavenegar SMS provider."
            ) from exc

        self._client = KavenegarAPI(api_key)
        self._sender = sender
        self._api_errors = (APIException, HTTPException)

    def send(self, phone_number: str, message: str) -> None:
        payload: Dict[str, str] = {"receptor": phone_number, "message": message}
        if self._sender:
            payload["sender"] = self._sender

        try:
            self._client.sms_send(payload)
        except self._api_errors as exc:  # pragma: no cover - network failure paths
            logger.exception("Kavenegar SMS send failed")
            raise


@lru_cache(maxsize=1)
def get_sms_provider() -> BaseSMSProvider:
    """Return an instance of the configured SMS provider."""

    provider_name = getattr(settings, "SMS_PROVIDER", "console")
    if not provider_name:
        provider_name = "console"

    normalized = provider_name.lower()

    if normalized == "console":
        return ConsoleSMSProvider()

    if normalized == "kavenegar":
        api_key = getattr(settings, "SMS_API_KEY", None)
        if not api_key:
            raise SMSConfigurationError(
                "SMS_API_KEY must be set when using the Kavenegar SMS provider."
            )

        sender = getattr(settings, "SMS_SENDER", None)
        return KavenegarSMSProvider(api_key=api_key, sender=sender)

    raise SMSConfigurationError(f"Unsupported SMS provider '{provider_name}'.")


def really_send_sms(phone_number: str, message: str) -> None:
    """Dispatch an SMS message through the configured provider."""

    provider = get_sms_provider()
    provider.send(phone_number, message)
