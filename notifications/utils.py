from notifications.models import Notification
from celery import shared_task

# --- تسک Celery برای ارسال SMS
@shared_task
def send_sms_task(phone_number, message):
    # اینجا کد واقعی ارسال SMS یا فراخوانی درگاه SMS میره
    print(f"Sending SMS to {phone_number}: {message}")

def send_site_notification(user, title, message, type_=Notification.Type.APPOINTMENT_REMINDER):
    """
    ایجاد نوتیفیکیشن در دیتابیس
    """
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=type_,
    )

def send_notification(user, title, message, type_=Notification.Type.APPOINTMENT_REMINDER):
    """
    Wrapper عمومی برای ارسال هر نوع نوتیفیکیشن
    """
    send_site_notification(user, title, message, type_)

# --- توابع مخصوص chat ---
def send_chat_notification(user, message):
    """
    ارسال نوتیفیکیشن برای پیام‌های چت
    """
    title = "New Chat Message"
    send_site_notification(user, title, message, type_=Notification.Type.APPOINTMENT_REMINDER)

def send_push_notification(user, title, message):
    """
    این تابع می‌تواند بعداً برای push notification واقعی استفاده شود
    """
    send_site_notification(user, title, message, type_=Notification.Type.APPOINTMENT_REMINDER)