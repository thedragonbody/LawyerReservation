from django.utils.timezone import now, timedelta
from celery import shared_task
from appointments.models import OnlineAppointment
from notifications.models import Notification
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


def send_upcoming_appointment_notifications():
    """
    ارسال نوتیفیکیشن و پیامک برای جلسات آنلاین 24 ساعت آینده
    """
    upcoming_time = now() + timedelta(hours=24)
    appointments = OnlineAppointment.objects.filter(
        status='CONFIRMED',
        slot__start_time__lte=upcoming_time,
        slot__start_time__gte=now()
    )

    for appt in appointments:
        if not Notification.objects.filter(appointment=appt, title="جلسه آینده").exists():
            Notification.objects.create(
                user=appt.client.user,
                appointment=appt,
                title="جلسه آینده",
                message=f"جلسه شما با {appt.lawyer.user.get_full_name()} در {appt.slot.start_time} نزدیک است."
            )
            # ارسال پیامک
            really_send_sms(
                appt.client.user.phone_number,
                f"جلسه شما با {appt.lawyer.user.get_full_name()} در {appt.slot.start_time} نزدیک است."
            )