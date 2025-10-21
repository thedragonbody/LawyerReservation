from celery import shared_task
import logging
from django.apps import apps
from django.utils import timezone

logger = logging.getLogger("celery")

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
        # مطمئن می‌شویم که طول UA از 512 کاراکتر ClientProfile تجاوز نکند
        ua = user_agent[:512] 
        # منطق استخراج نام دستگاه
        name = ua.split(')')[-1].strip() if ua else ''

        # 1. ثبت یا بروزرسانی دستگاه در مدل Device
        # اگر دستگاه با IP و UA یکسان موجود باشد، فقط last_seen بروزرسانی می‌شود
        Device.objects.update_or_create(
            client=cp,
            ip_address=ip,
            user_agent=ua,
            defaults={'name': name, 'revoked': False, 'last_seen': timezone.now()}
        )
        
        # 2. بروزرسانی آخرین لاگین در ClientProfile
        cp.last_login_ip = ip
        cp.last_login_user_agent = ua
        cp.save(update_fields=['last_login_ip', 'last_login_user_agent'])
        
        logger.info(f"Device registration success for User ID: {user_id} via Celery. IP: {ip}")
        
    except User.DoesNotExist:
        logger.error(f"User ID {user_id} not found for device registration.")
    except Exception as e:
        logger.error(f"Celery failed to register device for User ID {user_id}: {e}")