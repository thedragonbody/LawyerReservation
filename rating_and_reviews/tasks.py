from celery import shared_task
from django.contrib.auth import get_user_model
from notifications.utils import send_notification
import logging

logger = logging.getLogger("celery")
User = get_user_model()

@shared_task
def notify_lawyer_of_new_review_task(lawyer_user_id, client_full_name, rating):
    """
    وظیفه Celery برای ارسال نوتیفیکیشن به وکیل درباره یک ریویو جدید.
    """
    try:
        lawyer_user = User.objects.get(id=lawyer_user_id)
        
        title = "📝 نظر جدید درباره شما"
        message = f"{client_full_name} یک نظر جدید با امتیاز {rating} داده است."

        # send_notification احتمالا شامل ارسال SMS و نوتیفیکیشن دیتابیسی است.
        send_notification(
            lawyer_user,
            title=title,
            message=message
        )
        logger.info(f"Review notification sent via Celery to Lawyer ID: {lawyer_user_id}")

    except User.DoesNotExist:
        logger.error(f"Lawyer user with ID {lawyer_user_id} not found for review notification.")
    except Exception as e:
        logger.error(f"Failed to send review notification for Lawyer ID {lawyer_user_id}: {e}")