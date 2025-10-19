from django.utils import timezone
from datetime import timedelta
from notifications.models import Notification
from notifications.utils import send_sms
from .models import OnlineAppointment

def send_appointment_reminders():
    """
    ارسال خودکار یادآور برای جلسات آنلاین که در یک ساعت آینده برگزار می‌شن.
    """
    now = timezone.now()
    upcoming = OnlineAppointment.objects.filter(
        status="confirmed",
        start_time__lte=now + timedelta(hours=1),
        start_time__gte=now,
        is_reminder_sent=False
    )

    for appointment in upcoming:
        client_user = appointment.client.user
        lawyer_user = appointment.lawyer.user
        start_time = appointment.start_time.strftime("%Y-%m-%d %H:%M")

        # --- نوتیفیکیشن برای کاربر
        Notification.send(
            user=client_user,
            title="یادآوری جلسه آنلاین 🎥",
            message=f"جلسه آنلاین شما با {lawyer_user.get_full_name()} در {start_time} برگزار می‌شود.",
            type_=Notification.Type.APPOINTMENT_REMINDER,
        )
        send_sms(client_user.phone_number, f"یادآوری: جلسه آنلاین شما در {start_time} است 🎥")

        # --- نوتیفیکیشن برای وکیل
        Notification.send(
            user=lawyer_user,
            title="یادآوری جلسه نزدیک ⏰",
            message=f"جلسه شما با {client_user.get_full_name()} در {start_time} برگزار می‌شود.",
            type_=Notification.Type.APPOINTMENT_REMINDER,
        )
        send_sms(lawyer_user.phone_number, f"یادآوری: جلسه آنلاین در {start_time} برگزار می‌شود.")

        # --- علامت‌گذاری به عنوان ارسال‌شده
        appointment.is_reminder_sent = True
        appointment.save(update_fields=["is_reminder_sent"])