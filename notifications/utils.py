"""Utility helpers for working with notifications."""

from datetime import timedelta
from typing import Optional

from appointments.models import OnlineAppointment
from appointments.services.reminders import dispatch_upcoming_reminders
from appointments.utils import create_meeting_link as appointment_create_meeting_link
from notifications.models import Notification

from .sms_utils import really_send_sms


def create_meeting_link(appointment: OnlineAppointment, provider: str = "jitsi"):
    """Generate the online meeting link using the shared appointment helper."""

    return appointment_create_meeting_link(appointment, provider=provider)


def send_appointment_reminders(window: Optional[timedelta] = None):
    """Wrapper around :func:`dispatch_upcoming_reminders` with configurable window."""

    return dispatch_upcoming_reminders(window=window)


def send_sms(phone_number: str, message: str) -> None:
    """Relay SMS messages through the configured provider."""

    really_send_sms(phone_number, message)

def send_site_notification(user, title, message):
    """
    ارسال نوتیفیکیشن داخلی سایت
    """
    Notification.objects.create(
        user=user,
        title=title,
        message=message
    )

def send_chat_notification(user, message):
    """
    ارسال نوتیفیکیشن برای پیام‌های چت
    """
    Notification.objects.create(
        user=user,
        title="پیام جدید در چت",
        message=message
    )

def send_notification(
    user,
    title: str,
    message: str,
    *,
    type: str = Notification.Type.GENERAL,
    link: str | None = None,
) -> Notification:
    """Create a notification entry for the given user."""

    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=type,
        link=link,
    )


def send_push_notification(
    user,
    message: str,
    *,
    title: str = "اعلان پوش",
    type: str = Notification.Type.GENERAL,
    link: str | None = None,
) -> Notification:
    """Send a push notification by creating a standard notification entry."""

    return send_notification(user, title=title, message=message, type=type, link=link)
