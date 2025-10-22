from celery import shared_task
import logging
from django.apps import apps
from django.utils import timezone
import requests
from django.conf import settings

logger = logging.getLogger("celery")

# ==========================================================
# 1️⃣ ثبت یا بروزرسانی دستگاه کاربر (همان کد اصلی تو)
# ==========================================================
@shared_task
def register_device_task(user_id, ip_address, user_agent):
    """وظیفه غیرهمزمان ثبت یا بروزرسانی دستگاه کاربر و آخرین اطلاعات لاگین."""
    try:
        # ایمپورت مدل‌ها در داخل تابع برای جلوگیری از خطاهای Circular Import
        User = apps.get_model('users', 'User')
        ClientProfile = apps.get_model('client_profile', 'ClientProfile')
        Device = apps.get_model('client_profile', 'Device')

        user = User.objects.get(id=user_id)
        cp, _ = ClientProfile.objects.get_or_create(user=user)

        ip = ip_address
        ua = user_agent[:512]
        name = ua.split(')')[-1].strip() if ua else ''

        # ثبت یا بروزرسانی دستگاه
        Device.objects.update_or_create(
            client=cp,
            ip_address=ip,
            user_agent=ua,
            defaults={'name': name, 'revoked': False, 'last_seen': timezone.now()}
        )

        # بروزرسانی آخرین لاگین در ClientProfile
        cp.last_login_ip = ip
        cp.last_login_user_agent = ua
        cp.save(update_fields=['last_login_ip', 'last_login_user_agent'])

        logger.info(f"[register_device_task] Device registration success for User ID {user_id}, IP: {ip}")
        return True

    except User.DoesNotExist:
        logger.error(f"[register_device_task] User ID {user_id} not found for device registration.")
    except Exception as e:
        logger.error(f"[register_device_task] Celery failed for User ID {user_id}: {e}")
    return False


# ==========================================================
# 2️⃣ ارسال پیامک OTP یا اطلاع‌رسانی (Passwordless Login / OTP)
# ==========================================================
@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_sms_task(self, phone_number, message):
    """
    وظیفه‌ی غیرهمزمان ارسال پیامک (OTP یا اعلان).
    - اگر سرویس SMS در settings تعریف شده باشد (مثلاً Kavenegar/Twilio)، از آن استفاده می‌کند.
    - در غیر این صورت پیام در لاگ و کنسول چاپ می‌شود.
    """
    try:
        # ===========================
        # 📌 روش ۱: استفاده از provider داخلی مثل Kavenegar
        # ===========================
        provider = getattr(settings, "SMS_PROVIDER", "console")

        if provider == "kavenegar":
            api_key = getattr(settings, "KAVENEGAR_API_KEY", None)
            sender = getattr(settings, "KAVENEGAR_SENDER", None)
            if not api_key or not sender:
                raise ValueError("Kavenegar API credentials not set in settings.")

            url = "https://api.kavenegar.com/v1/{}/sms/send.json".format(api_key)
            payload = {"receptor": phone_number, "message": message, "sender": sender}
            response = requests.post(url, data=payload, timeout=5)

            if response.status_code == 200:
                logger.info(f"[send_sms_task] OTP sent to {phone_number}")
                return True
            else:
                raise Exception(f"Kavenegar API error: {response.text}")

        # ===========================
        # 📌 روش ۲: Twilio
        # ===========================
        elif provider == "twilio":
            from twilio.rest import Client
            account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
            auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
            from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)

            if not all([account_sid, auth_token, from_number]):
                raise ValueError("Twilio credentials not set in settings.")

            client = Client(account_sid, auth_token)
            message_obj = client.messages.create(
                body=message,
                from_=from_number,
                to=phone_number
            )
            logger.info(f"[send_sms_task] Twilio message SID: {message_obj.sid} sent to {phone_number}")
            return True

        # ===========================
        # 📌 روش ۳: پیش‌فرض (fallback – چاپ در لاگ)
        # ===========================
        else:
            print(f"[SMS FALLBACK] To: {phone_number} | Message: {message}")
            logger.warning(f"[send_sms_task] SMS fallback used for {phone_number}. Message: {message}")
            return True

    except requests.exceptions.RequestException as e:
        logger.error(f"[send_sms_task] Network error sending SMS to {phone_number}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"[send_sms_task] Failed to send SMS to {phone_number}: {e}")
        raise self.retry(exc=e)