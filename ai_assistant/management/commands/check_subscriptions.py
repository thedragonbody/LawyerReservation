from django.core.management.base import BaseCommand
from django.utils import timezone
from ai_assistant.models import Subscription
from datetime import timedelta
import logging

# 💡 تغییر ۱: وارد کردن ابزارهای صحیح
from common.utils import send_user_notification  # تابع یکپارچه برای DB + WebSocket
from AloVakil.celery import send_sms_task         # تسک غیرهمزمان Celery

logger = logging.getLogger("ai_assistant")

class Command(BaseCommand):
    help = "Deactivate expired subscriptions and notify users 3 days before expiration."

    def handle(self, *args, **options):
        now = timezone.now()
        
        # 1) Deactivate expired
        expired_count = Subscription.objects.filter(active=True, ends_at__lt=now).update(active=False)
        if expired_count:
            logger.info(f"Deactivated {expired_count} expired subscriptions.")
            self.stdout.write(self.style.SUCCESS(f"Deactivated {expired_count} subscriptions."))

        # 2) Notify 3 days before
        warn_date = now + timedelta(days=3)
        # استفاده از iterator() برای جلوگیری از بارگذاری همه در حافظه
        to_warn_subs = Subscription.objects.filter(
            active=True, 
            ends_at__date=warn_date.date()
        ).select_related('user') # بهینه‌سازی کوئری

        warned_count = 0
        for s in to_warn_subs.iterator():
            try:
                link = f"/payments/subscription/renew/{s.id}/" # فرض بر اینکه این URL بعدا ساخته می‌شود
                message = f"اشتراک AI شما در تاریخ {s.ends_at.date()} به پایان می‌رسد. جهت تمدید اقدام کنید."
                
                # 💡 تغییر ۲: استفاده از نوتیفیکیشن یکپارچه
                send_user_notification(
                    s.user, 
                    "هشدار پایان اشتراک", 
                    message,
                    link=link
                )

                # 💡 تغییر ۳: استفاده از Celery task (غیرهمزمان)
                if hasattr(s.user, "phone_number") and s.user.phone_number:
                    sms_message = f"اشتراک AI شما در {s.ends_at.date()} به پایان می‌رسد. {link}"
                    send_sms_task.delay(s.user.phone_number, sms_message)

                warned_count += 1
            except Exception as e:
                logger.exception(f"Failed to send reminder for subscription {s.id}: {e}")
        
        if warned_count:
            logger.info(f"Sent {warned_count} renewal reminders.")
            self.stdout.write(self.style.SUCCESS(f"Sent {warned_count} reminders."))

        self.stdout.write(self.style.SUCCESS("Check subscriptions job finished."))