import logging
from notifications.models import Notification
from common.utils import send_sms

logger = logging.getLogger("notifications")


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
        logger.info(f"Site notification created for {user.username}")
    except Exception as e:
        logger.warning(f"Failed to create site notification for {user.username}: {e}")


def send_notification(user, title: str, message: str, phone_number_field="phone_number"):
    """
    ارسال نوتیف داخلی + پیامک به کاربر
    """
    # نوتیف داخلی سایت
    send_site_notification(user, title, message)

    # ارسال SMS در صورت داشتن شماره
    phone_number = getattr(user, phone_number_field, None)
    if phone_number:
        try:
            send_sms(phone_number, f"{title}\n{message}")
        except Exception as e:
            logger.warning(f"Failed to send SMS to {phone_number}: {e}")
    else:
        logger.info(f"No phone number for user {user.username}, SMS skipped.")

        