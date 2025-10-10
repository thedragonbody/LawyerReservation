from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from ai_assistant.models import Subscription
from common.utils import send_user_notification, send_sms
from datetime import timedelta
import logging
from notifications.utils import send_site_notification

logger = logging.getLogger("ai_assistant")

class Command(BaseCommand):
    help = "Deactivate expired subscriptions and notify users 3 days before expiration."

    def handle(self, *args, **options):
        now = timezone.now()
        # 1) deactivate expired
        expired = Subscription.objects.filter(active=True, ends_at__lt=now)
        for s in expired:
            s.active = False
            s.save(update_fields=["active"])
            logger.info(f"Deactivated subscription {s.id} for user {s.user}")

        # 2) notify 3 days before
        warn_date = now + timedelta(days=3)
        to_warn = Subscription.objects.filter(active=True, ends_at__date=warn_date.date())
        for s in to_warn:
            try:
                link = f"/payments/subscription/renew/{s.id}/"
                message = f"اشتراک شما در {s.ends_at.date()} به پایان می‌رسد. آیا می‌خواهید تمدید کنید؟ {link}"

                #  نوتیف سایت (WebSocket)
                send_site_notification(s.user, "هشدار پایان اشتراک", message)

                #  پیامک (در صورت وجود شماره)
                if hasattr(s.user, "phone_number") and s.user.phone_number:
                    send_sms(s.user.phone_number, f"اشتراک شما در {s.ends_at.date()} به پایان می‌رسد. برای تمدید: {link}")

                logger.info(f"Sent renewal reminder to {s.user}")
            except Exception as e:
                logger.exception("Failed to send reminder: %s", e)