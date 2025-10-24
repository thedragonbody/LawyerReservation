"""Celery tasks for the appointments app."""

from celery import shared_task

from appointments.services import dispatch_upcoming_reminders


@shared_task(name="appointments.tasks.send_appointment_reminders_task")
def send_appointment_reminders_task() -> int:
    """Schedule-friendly wrapper around ``dispatch_upcoming_reminders``."""

    return dispatch_upcoming_reminders()


__all__ = ["send_appointment_reminders_task"]
