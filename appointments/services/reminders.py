"""Service helpers for sending appointment reminders."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Iterable, Optional

from django.db import transaction
from django.utils import timezone

from appointments.models import OnlineAppointment
from common.choices import AppointmentStatus
from notifications.models import Notification
from common.utils import send_sms


@dataclass
class ReminderDispatchResult:
    """Represents the channels that were used to notify a user."""

    push_sent: bool = False
    sms_sent: bool = False


def resolve_user_channel_preferences(user) -> Dict[str, bool]:
    """Return a mapping of enabled notification channels for ``user``."""

    preferences = {"push": True, "sms": True}
    for relation_name in ("client_profile", "lawyer_profile"):
        profile = getattr(user, relation_name, None)
        if profile is None:
            continue
        preferences["push"] = getattr(
            profile, "receive_push_notifications", preferences["push"]
        )
        preferences["sms"] = getattr(
            profile, "receive_sms_notifications", preferences["sms"]
        )
    return preferences


def send_reminder_to_user(
    *,
    user,
    title: str,
    message: str,
    sms_message: Optional[str] = None,
) -> ReminderDispatchResult:
    """Send a reminder message to ``user`` honouring their channel preferences."""

    preferences = resolve_user_channel_preferences(user)
    result = ReminderDispatchResult()

    if preferences.get("push", True):
        Notification.send(
            user=user,
            title=title,
            message=message,
            type_=Notification.Type.APPOINTMENT_REMINDER,
        )
        result.push_sent = True

    if preferences.get("sms", True) and sms_message and user.phone_number:
        send_sms(user.phone_number, sms_message)
        result.sms_sent = True

    return result


def _format_slot_time(appointment: OnlineAppointment) -> str:
    slot_start = timezone.localtime(appointment.slot.start_time)
    return slot_start.strftime("%Y-%m-%d %H:%M")


def _get_upcoming_online_appointments(
    *,
    window: timedelta,
) -> Iterable[OnlineAppointment]:
    now = timezone.now()
    return (
        OnlineAppointment.objects.filter(
            status=AppointmentStatus.CONFIRMED,
            slot__start_time__gte=now,
            slot__start_time__lte=now + window,
            is_reminder_sent=False,
        )
        .select_related("client__user", "lawyer__user", "slot")
        .order_by("slot__start_time")
    )


def dispatch_upcoming_reminders(*, window: timedelta = timedelta(hours=1)) -> int:
    """Send reminders for confirmed appointments whose slot starts soon."""

    processed = 0
    appointments = list(_get_upcoming_online_appointments(window=window))

    for appointment in appointments:
        start_time_display = _format_slot_time(appointment)

        client_user = appointment.client.user
        lawyer_user = appointment.lawyer.user

        client_message = (
            f"جلسه آنلاین شما با {lawyer_user.get_full_name()} در {start_time_display} برگزار می‌شود."
        )
        lawyer_message = (
            f"جلسه شما با {client_user.get_full_name()} در {start_time_display} برگزار می‌شود."
        )

        send_reminder_to_user(
            user=client_user,
            title="یادآوری جلسه آنلاین 🎥",
            message=client_message,
            sms_message=f"یادآوری: جلسه آنلاین شما در {start_time_display} است 🎥",
        )

        send_reminder_to_user(
            user=lawyer_user,
            title="یادآوری جلسه نزدیک ⏰",
            message=lawyer_message,
            sms_message=f"یادآوری: جلسه آنلاین در {start_time_display} برگزار می‌شود.",
        )

        with transaction.atomic():
            appointment.is_reminder_sent = True
            appointment.save(update_fields=["is_reminder_sent"])

        processed += 1

    return processed


__all__ = [
    "ReminderDispatchResult",
    "dispatch_upcoming_reminders",
    "resolve_user_channel_preferences",
    "send_reminder_to_user",
]
