"""Celery tasks for the appointments app."""

from datetime import timedelta
from typing import Optional

from celery import shared_task
from django.utils import timezone

from appointments.integrations import OAuthIntegrationError, get_oauth_client
from appointments.services import dispatch_upcoming_reminders
from users.models import OAuthToken


@shared_task(name="appointments.tasks.send_appointment_reminders_task")
def send_appointment_reminders_task(window_minutes: Optional[float] = None):
    """Schedule-friendly wrapper around ``dispatch_upcoming_reminders``."""

    window = None
    if window_minutes is not None:
        window = timedelta(minutes=float(window_minutes))
    return dispatch_upcoming_reminders(window=window)


@shared_task(name="appointments.tasks.refresh_expiring_oauth_tokens")
def refresh_expiring_oauth_tokens() -> int:
    """Refresh OAuth tokens that are about to expire."""

    threshold = timezone.now() + timedelta(minutes=15)
    tokens = OAuthToken.objects.filter(
        expires_at__isnull=False,
        expires_at__lte=threshold,
        refresh_token__isnull=False,
    ).select_related("user")

    refreshed = 0
    for token in tokens:
        try:
            client = get_oauth_client(token.provider)
            payload = client.refresh_token(token.refresh_token)
            token.mark_refreshed(
                expires_in=payload.get("expires_in"),
                access_token=payload.get("access_token"),
                refresh_token=payload.get("refresh_token"),
                scope=payload.get("scope"),
                token_type=payload.get("token_type"),
            )
            refreshed += 1
        except OAuthIntegrationError:
            continue

    return refreshed


__all__ = [
    "send_appointment_reminders_task",
    "refresh_expiring_oauth_tokens",
]
