"""OAuth helpers for calendar integrations."""

from __future__ import annotations

from datetime import timedelta
from typing import Dict
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone
from django.utils.crypto import get_random_string


class OAuthIntegrationError(Exception):
    """Raised when an OAuth operation fails."""


STATE_SALT = "appointments.calendar.oauth"
STATE_TTL_SECONDS = getattr(settings, "CALENDAR_OAUTH_STATE_TTL", 300)


class BaseOAuthClient:
    authorization_base_url: str
    token_url: str
    scope: tuple[str, ...]

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def build_authorization_url(self, state: str) -> str:
        raise NotImplementedError

    def exchange_code(self, code: str) -> Dict[str, str]:
        raise NotImplementedError

    def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        raise NotImplementedError


class GoogleOAuthClient(BaseOAuthClient):
    authorization_base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    scope = (
        "https://www.googleapis.com/auth/calendar.events",
    )

    def build_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scope),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        return f"{self.authorization_base_url}?{urlencode(params)}"

    def exchange_code(self, code: str) -> Dict[str, str]:
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        return self._request_token(data)

    def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        data = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }
        return self._request_token(data)

    def _request_token(self, data: Dict[str, str]) -> Dict[str, str]:
        try:
            response = requests.post(self.token_url, data=data, timeout=10)
        except requests.RequestException as exc:  # pragma: no cover - network errors are rare in tests
            raise OAuthIntegrationError("امکان برقراری ارتباط با سرویس OAuth وجود ندارد.") from exc
        try:
            payload = response.json() if response.content else {}
        except ValueError as exc:
            raise OAuthIntegrationError("پاسخ OAuth نامعتبر است.") from exc
        if response.status_code != 200:
            description = payload.get("error_description") or payload.get("error") or "OAuth exchange failed"
            raise OAuthIntegrationError(description)
        return payload


def get_oauth_client(provider: str) -> BaseOAuthClient:
    provider = provider.lower()
    if provider != "google":
        raise OAuthIntegrationError(f"Unknown OAuth provider: {provider}")

    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    redirect_uri = getattr(
        settings,
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://localhost:8000/appointments/calendar/oauth/google/callback/",
    )

    if not client_id or not client_secret:
        raise OAuthIntegrationError("Google OAuth credentials are not configured.")

    return GoogleOAuthClient(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)


def build_state_for_user(user, provider: str) -> str:
    payload = {
        "user_id": user.pk,
        "provider": provider,
        "nonce": get_random_string(16),
        "issued_at": timezone.now().timestamp(),
    }
    return signing.dumps(payload, salt=STATE_SALT)


def resolve_state(state: str, provider: str):
    try:
        payload = signing.loads(state, salt=STATE_SALT, max_age=STATE_TTL_SECONDS)
    except signing.BadSignature as exc:
        raise OAuthIntegrationError("اعتبار state به پایان رسیده یا نامعتبر است.") from exc

    if payload.get("provider") != provider:
        raise OAuthIntegrationError("ارائه‌دهنده OAuth با state مطابقت ندارد.")

    user_id = payload.get("user_id")
    User = get_user_model()
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise OAuthIntegrationError("کاربر مرتبط با state یافت نشد.") from exc


def extract_expiry(token_payload: Dict[str, str]):
    expires_in = token_payload.get("expires_in")
    if expires_in is None:
        return None
    try:
        expires_in = int(expires_in)
    except (TypeError, ValueError):
        return None
    return timezone.now() + timedelta(seconds=expires_in)


__all__ = [
    "OAuthIntegrationError",
    "BaseOAuthClient",
    "GoogleOAuthClient",
    "get_oauth_client",
    "build_state_for_user",
    "resolve_state",
    "extract_expiry",
]
