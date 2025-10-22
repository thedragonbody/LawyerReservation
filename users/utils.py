from .tasks import register_device_task
from django.conf import settings

def register_device_for_user(user, request):
    """
    فراخوانی وظیفه Celery برای ثبت دستگاه؛ اگر Celery در دسترس نبود،
    تلاش می‌کنیم fallback sync داشته باشیم (اگر task قابل فراخوانی sync باشد).
    """
    ip = request.META.get('REMOTE_ADDR')
    ua = request.META.get('HTTP_USER_AGENT', '')
    try:
        register_device_task.delay(user_id=user.id, ip_address=ip, user_agent=ua)
    except Exception:
        # fallback synchronous اگر task به شکل عادی قابل فراخوانی باشد
        try:
            register_device_task(user.id, ip, ua)
        except Exception:
            pass


def send_sms_task_or_sync(phone_number, message):
    """
    اگر task celery برای ارسال پیامک تعریف شده باشد آن را با .delay فراخوانی می‌کنیم.
    در غیر این صورت fallback sync (در حال حاضر فقط print/log) اجرا می‌شود.
    حتماً این تابع را به provider واقعی پیامک (Twilio/Kavenegar/...) وصل کن.
    """
    try:
        # اگر task celery موجود باشد
        from .tasks import send_sms_task
        # اگر Celery + broker پیکربندی شده باشند، این خط .delay کار می‌کند
        return send_sms_task.delay(phone_number, message)
    except Exception:
        # fallback ساده (dev): فقط log/print
        print(f"[SMS FALLBACK] To: {phone_number} Message: {message}")
        return None