"""Service helpers for sending appointment reminders."""

import logging
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Iterable, Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from appointments.models import OnlineAppointment
from common.choices import AppointmentStatus
from notifications.models import Notification
from common.utils import send_sms

logger = logging.getLogger(__name__)


@dataclass
class ReminderDispatchResult:
    """Represents the channels that were used to notify a user."""

    push_attempted: bool = False
    push_sent: bool = False
    push_error: Optional[Exception] = None
    sms_attempted: bool = False
    sms_sent: bool = False
    sms_error: Optional[Exception] = None


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
        result.push_attempted = True
        try:
            Notification.send(
                user=user,
                title=title,
                message=message,
                type_=Notification.Type.APPOINTMENT_REMINDER,
            )
            result.push_sent = True
        except Exception as exc:  # pragma: no cover - defensive logging path
            result.push_error = exc

    if preferences.get("sms", True) and sms_message and user.phone_number:
        result.sms_attempted = True
        try:
            send_sms(user.phone_number, sms_message)
            result.sms_sent = True
        except Exception as exc:  # pragma: no cover - defensive logging path
            result.sms_error = exc

    return result


def _resolve_default_window() -> timedelta:
    """Determine the default reminder window from settings or the environment."""

    configured = getattr(settings, "APPOINTMENT_REMINDER_WINDOW", None)
    if isinstance(configured, timedelta):
        return configured
    if configured not in (None, ""):
        try:
            return timedelta(minutes=float(configured))
        except (TypeError, ValueError):
            logger.warning(
                "Invalid APPOINTMENT_REMINDER_WINDOW %r in settings; using fallback.",
                configured,
            )

    env_value = os.getenv("APPOINTMENT_REMINDER_WINDOW")
    if env_value not in (None, ""):
        try:
            return timedelta(minutes=float(env_value))
        except (TypeError, ValueError):
            logger.warning(
                "Invalid APPOINTMENT_REMINDER_WINDOW %r in environment; using fallback.",
                env_value,
            )

    return timedelta(hours=1)


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


def dispatch_upcoming_reminders(*, window: Optional[timedelta] = None) -> Dict[str, Any]:
    """Send reminders for confirmed appointments whose slot starts soon."""

    if window is None:
        window = _resolve_default_window()

    summary = {
        "processed_appointments": 0,
        "notifications": {
            "push": {"sent": 0, "failed": 0},
            "sms": {"sent": 0, "failed": 0},
        },
        "errors": [],
        "window": window,
    }

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

        client_result = send_reminder_to_user(
            user=client_user,
            title="یادآوری جلسه آنلاین 🎥",
            message=client_message,
            sms_message=f"یادآوری: جلسه آنلاین شما در {start_time_display} است 🎥",
        )

        lawyer_result = send_reminder_to_user(
            user=lawyer_user,
            title="یادآوری جلسه نزدیک ⏰",
            message=lawyer_message,
            sms_message=f"یادآوری: جلسه آنلاین در {start_time_display} برگزار می‌شود.",
        )

        for user, result, role in (
            (client_user, client_result, "client"),
            (lawyer_user, lawyer_result, "lawyer"),
        ):
            if result.push_attempted:
                if result.push_sent:
                    summary["notifications"]["push"]["sent"] += 1
                    logger.info(
                        "Sent push reminder for appointment %s to %s user %s",
                        appointment.id,
                        role,
                        user.id,
                    )
                else:
                    summary["notifications"]["push"]["failed"] += 1
                    summary["errors"].append(
                        {
                            "appointment_id": appointment.id,
                            "user_id": user.id,
                            "channel": "push",
                            "role": role,
                            "error": str(result.push_error),
                        }
                    )
                    if result.push_error is not None:
                        logger.error(
                            "Failed to send push reminder for appointment %s to %s user %s: %s",
                            appointment.id,
                            role,
                            user.id,
                            result.push_error,
                            exc_info=(
                                type(result.push_error),
                                result.push_error,
                                result.push_error.__traceback__,
                            ),
                        )

            if result.sms_attempted:
                if result.sms_sent:
                    summary["notifications"]["sms"]["sent"] += 1
                    logger.info(
                        "Sent SMS reminder for appointment %s to %s user %s",
                        appointment.id,
                        role,
                        user.id,
                    )
                else:
                    summary["notifications"]["sms"]["failed"] += 1
                    summary["errors"].append(
                        {
                            "appointment_id": appointment.id,
                            "user_id": user.id,
                            "channel": "sms",
                            "role": role,
                            "error": str(result.sms_error),
                        }
                    )
                    if result.sms_error is not None:
                        logger.error(
                            "Failed to send SMS reminder for appointment %s to %s user %s: %s",
                            appointment.id,
                            role,
                            user.id,
                            result.sms_error,
                            exc_info=(
                                type(result.sms_error),
                                result.sms_error,
                                result.sms_error.__traceback__,
                            ),
                        )

        with transaction.atomic():
            appointment.is_reminder_sent = True
            appointment.save(update_fields=["is_reminder_sent"])

        summary["processed_appointments"] += 1

    return summary


__all__ = [
    "ReminderDispatchResult",
    "dispatch_upcoming_reminders",
    "resolve_user_channel_preferences",
    "send_reminder_to_user",
]
