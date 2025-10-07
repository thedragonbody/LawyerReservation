import logging
from notifications.models import Notification
from common.utils import send_sms
import firebase_admin
from firebase_admin import credentials, messaging, initialize_app
from django.conf import settings

logger = logging.getLogger("notifications")

# ------------------- Initialize Firebase once -------------------
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_JSON)
    firebase_admin.initialize_app(cred)

# ------------------- Site Notifications -------------------
def send_site_notification(user, title: str, message: str):
    """
    ایجاد نوتیف داخلی در سایت (مدل Notification)
    """
    try:
        Notification.objects.create(
            user=user,
            title=title,
            message=message
        )
        logger.info(f"✅ Site notification created for {user.username}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to create site notification for {user.username}: {e}")


# ------------------- SMS + Site Notifications -------------------
def send_notification(user, title: str, message: str, phone_number_field="phone_number"):
    """
    ارسال نوتیف داخلی + پیامک (در صورت وجود شماره)
    """
    # 1️⃣ ایجاد نوتیف در سایت
    send_site_notification(user, title, message)

    # 2️⃣ ارسال پیامک در صورت وجود شماره
    phone_number = getattr(user, phone_number_field, None)
    if phone_number:
        try:
            send_sms(phone_number, f"{title}\n{message}")
            logger.info(f"📱 SMS sent to {phone_number}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to send SMS to {phone_number}: {e}")
    else:
        logger.info(f"ℹ️ No phone number for user {user.username}, SMS skipped.")


# ------------------- Chat Notifications -------------------
def send_chat_notification(sender, receiver, message_text: str):
    """
    ارسال نوتیف مخصوص پیام جدید در چت بین وکیل و کلاینت
    """
    title = f"📩 پیام جدید از {sender.get_full_name()}"
    message = f"{message_text[:100]}..." if len(message_text) > 100 else message_text

    try:
        send_notification(receiver, title, message)
        send_push_notification(receiver, title, message)
        logger.info(f"💬 Chat notification sent to {receiver.username}")
    except Exception as e:
        logger.error(f"❌ Failed to send chat notification to {receiver.username}: {e}")


# ------------------- Push Notification -------------------
def send_push_notification(user, title: str, message: str, data=None):
    """
    ارسال push notification به دستگاه موبایل (FCM)
    """
    # انتظار می‌رود کاربر مدل User یک فیلد device_token داشته باشد
    device_token = getattr(user, "device_token", None)
    if not device_token:
        logger.info(f"ℹ️ No device token for {user.username}, push skipped.")
        return

    fcm_message = messaging.Message(
        notification=messaging.Notification(title=title, body=message),
        token=device_token,
        data=data or {}
    )

    try:
        response = messaging.send(fcm_message)
        logger.info(f"🚀 Push notification sent to {user.username}, response: {response}")
    except Exception as e:
        logger.error(f"❌ Failed to send push notification to {user.username}: {e}")