import logging
from django.core.mail import send_mail
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from notifications.models import Notification
from notifications.serializers import NotificationSerializer
import requests
from django.conf import settings
import re
import unicodedata

logger = logging.getLogger("common")

def send_user_notification(user, title, message, link=None):
    """
    ذخیره در DB + WebSocket + push + email (fallback logged)
    """
    try:
        notification = Notification.objects.create(user=user, title=title, message=message, link=link)
    except Exception as e:
        logger.error("Failed to create DB notification: %s", e)
        notification = None

    # WebSocket
    try:
        if notification:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user.id}',
                {"type": "send_notification", "message": NotificationSerializer(notification).data}
            )
    except Exception as e:
        logger.warning("WebSocket notify failed: %s", e)

def send_sms(phone_number: str, message: str):
    """
    نمونه سادهٔ ارسال SMS با Kavenegar (تغییر دهید به سرویس دلخواه)
    از اجرای بلادرنگ بهتر است در تولید از queue مثل Celery استفاده شود.
    """
    if not phone_number:
        logger.info("No phone number provided, skip SMS.")
        return
    try:
        api_key = getattr(settings, "SMS_API_KEY", None)
        if not api_key:
            logger.info("SMS_API_KEY not set; skipping SMS send.")
            return
        url = f"https://api.kavenegar.com/v1/{api_key}/sms/send.json"
        payload = {"receptor": phone_number, "message": message}
        resp = requests.post(url, data=payload, timeout=8)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("SMS sending failed for %s: %s", phone_number, e)

def normalize_text(text: str) -> str:
    """
    پاکسازی متن برای جستجو — حذف فاصله‌های اضافی، 
    نرمال‌سازی کاراکترهای فارسی و انگلیسی، و حذف علائم.
    """
    if not text:
        return ""
    
    # نرمال‌سازی یونیکد
    text = unicodedata.normalize("NFKC", text)

    # جایگزینی حروف عربی به فارسی
    replacements = {
        "ي": "ی",
        "ك": "ک",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # حذف کاراکترهای غیر ضروری
    text = re.sub(r"[^0-9آ-یA-Za-z\s@.]", " ", text)
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()