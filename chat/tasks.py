from celery import shared_task
from django.contrib.auth import get_user_model
from notifications.utils import send_chat_notification, send_push_notification
import logging

logger = logging.getLogger("celery")
User = get_user_model()

@shared_task
def send_chat_notifications_task(sender_id, receiver_id, message_text):
    """
    وظیفه Celery برای ارسال نوتیفیکیشن و پیامک در پس‌زمینه.
    """
    try:
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)

        # 1. ارسال نوتیفیکیشن دیتابیسی (و پیامک)
        # فرض می‌شود send_chat_notification شامل منطق send_sms است
        send_chat_notification(sender, receiver, message_text)
        logger.info(f"Chat notification sent via Celery from {sender.id} to {receiver.id}")
        
        # 2. ارسال پوش نوتیفیکیشن (اختیاری)
        # اگر send_chat_notification شامل این نیست، اینجا اضافه کنید:
        # send_push_notification(receiver, "پیام جدید", message_text) 

    except User.DoesNotExist:
        logger.error("Sender or receiver user does not exist for chat notification.")
    except Exception as e:
        logger.error(f"Failed to send chat notifications: {e}")