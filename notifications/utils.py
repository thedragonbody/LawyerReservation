from datetime import timedelta

from django.utils import timezone

from appointments.models import OnlineAppointment
from appointments.utils import create_meeting_link as appointment_create_meeting_link
from notifications.models import Notification
from .sms_utils import really_send_sms  # استفاده مستقیم از ماژول مستقل
"""Utility helpers for working with notifications."""

import uuid
from datetime import timedelta

from appointments.models import OnlineAppointment
from notifications.models import Notification

from .sms_utils import really_send_sms
from appointments.services.reminders import dispatch_upcoming_reminders


def create_meeting_link(appointment: OnlineAppointment, provider: str = "jitsi"):
    """
    تولید لینک جلسه آنلاین (Jitsi یا Google Meet)
    """
    return appointment_create_meeting_link(appointment, provider=provider)
    if provider == "jitsi":
        meeting_id = f"alovakil-{appointment.id}-{uuid.uuid4().hex[:8]}"
        base = "https://meet.jit.si"
        return f"{base}/{meeting_id}"
    else:
        return None


def send_appointment_reminders():
    """Wrapper around :func:`dispatch_upcoming_reminders` with default window."""

    return dispatch_upcoming_reminders(window=timedelta(hours=1))


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

def send_push_notification(user, message):
    """
    ارسال پوش نوتیفیکیشن
    """
    # اینجا می‌تونی integration با FCM یا OneSignal اضافه کنی
    Notification.objects.create(
        user=user,
        title="اعلان پوش",
def send_push_notification(user, message, *, title: str = "اعلان پوش"):
    """Send a push notification using the console provider implementation."""

    Notification.objects.create(
        user=user,
        title=title,
        message=message,
    )
    

def send_notification(user, title, message):
    """
    ارسال یک نوتیفیکیشن عمومی
    """
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        message=message
    )
