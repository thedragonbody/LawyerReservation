from datetime import timedelta
from typing import Optional

from celery import shared_task
from appointments.services.reminders import dispatch_upcoming_reminders

from .sms_utils import really_send_sms  # از ماژول مستقل import شود

@shared_task(bind=True, default_retry_delay=60, max_retries=3)
def send_sms_task(self, phone_number, message):
    """
    اجرای وظیفه Celery برای ارسال پیامک با retry
    """
    try:
        really_send_sms(phone_number, message)
    except Exception as exc:
        raise self.retry(exc=exc)



def send_upcoming_appointment_notifications(window_hours: Optional[float] = None):
    """Delegate reminder sending to the shared appointments reminder service."""

    window = None
    if window_hours is not None:
        window = timedelta(hours=float(window_hours))
    return dispatch_upcoming_reminders(window=window)
