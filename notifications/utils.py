from notifications.models import Notification
from django.conf import settings
from celery import shared_task

# ----------------------------
# تسک Celery برای ارسال SMS
# ----------------------------
@shared_task
def send_sms_task(phone_number, message):
    """
    ارسال SMS (در صورت استفاده از Celery)
    """
    # اینجا کد واقعی ارسال SMS یا فراخوانی درگاه SMS قرار می‌گیرد
    print(f"Sending SMS to {phone_number}: {message}")


# ----------------------------
# نوتیفیکیشن سایت
# ----------------------------
def send_site_notification(user, title, message, type_=Notification.Type.APPOINTMENT_REMINDER):
    """
    ایجاد نوتیفیکیشن در دیتابیس بدون circular import
    """
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=type_,
    )


# ----------------------------
# نوتیفیکیشن چت
# ----------------------------
def send_chat_notification(user, message):
    """
    ارسال نوتیفیکیشن هنگام دریافت پیام چت
    """
    title = "پیام جدید"
    send_site_notification(user, title, message, type_=Notification.Type.APPOINTMENT_REMINDER)
    # در صورت نیاز می‌توانید اینجا SMS یا Push هم اضافه کنید


# ----------------------------
# نوتیفیکیشن پوش
# ----------------------------
def send_push_notification(user, title, message):
    """
    ارسال نوتیفیکیشن Push
    """
    # اینجا کد اتصال به سرویس Push (مثل FCM یا OneSignal) قرار می‌گیرد
    print(f"Push notification to {user.email}: {title} - {message}")
    # همزمان دیتابیس هم می‌توان ذخیره کرد
    send_site_notification(user, title, message, type_=Notification.Type.APPOINTMENT_REMINDER)