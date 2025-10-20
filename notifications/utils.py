import uuid
from typing import TYPE_CHECKING
from django.utils import timezone
from datetime import timedelta
from notifications.models import Notification
from .sms_utils import really_send_sms  # استفاده مستقیم از ماژول مستقل
from notifications.models import Notification

if TYPE_CHECKING:
    from .models import OnlineAppointment


def create_meeting_link(appointment: "OnlineAppointment", provider="jitsi"):
    """
    تولید لینک جلسه آنلاین (Jitsi یا Google Meet)
    """
    if provider == "jitsi":
        meeting_id = f"alovakil-{appointment.id}-{uuid.uuid4().hex[:8]}"
        base = "https://meet.jit.si"
        return f"{base}/{meeting_id}"
    else:
        # TODO: Google Meet API integration
        return None


def send_appointment_reminders():
    """
    ارسال یادآور برای جلسات آنلاین که در یک ساعت آینده برگزار می‌شوند
    """
    now_time = timezone.now()
    upcoming = OnlineAppointment.objects.filter(
        status="CONFIRMED",
        start_time__lte=now_time + timedelta(hours=1),
        start_time__gte=now_time,
        is_reminder_sent=False
    )

    for appointment in upcoming:
        client_user = appointment.client.user
        lawyer_user = appointment.lawyer.user
        start_time = appointment.start_time.strftime("%Y-%m-%d %H:%M")

        # نوتیفیکیشن برای کاربر
        Notification.send(
            user=client_user,
            title="یادآوری جلسه آنلاین 🎥",
            message=f"جلسه آنلاین شما با {lawyer_user.get_full_name()} در {start_time} برگزار می‌شود.",
            type_=Notification.Type.APPOINTMENT_REMINDER,
        )
        really_send_sms(client_user.phone_number, f"یادآوری: جلسه آنلاین شما در {start_time} است 🎥")

        # نوتیفیکیشن برای وکیل
        Notification.send(
            user=lawyer_user,
            title="یادآوری جلسه نزدیک ⏰",
            message=f"جلسه شما با {client_user.get_full_name()} در {start_time} برگزار می‌شود.",
            type_=Notification.Type.APPOINTMENT_REMINDER,
        )
        really_send_sms(lawyer_user.phone_number, f"یادآوری: جلسه آنلاین در {start_time} برگزار می‌شود.")

        # علامت‌گذاری به عنوان ارسال‌شده
        appointment.is_reminder_sent = True
        appointment.save(update_fields=["is_reminder_sent"])

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
            message=message
        )
    

def send_notification(user, title, message):
    """
    ارسال یک نوتیفیکیشن عمومی
    """
    Notification.objects.create(
        user=user,
        title=title,
        message=message
    )