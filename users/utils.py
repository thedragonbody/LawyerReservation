from .tasks import register_device_task 
# 💡 حذف ایمپورت‌های client_profile برای جلوگیری از Circular Import

def register_device_for_user(user, request):
    """
    وظیفه Celery را برای ثبت یا بروزرسانی دستگاه هنگام ورود فراخوانی می‌کند.
    """
    ip = request.META.get('REMOTE_ADDR')
    ua = request.META.get('HTTP_USER_AGENT', '') 
    
    # فراخوانی Celery Task به صورت غیرهمزمان
    register_device_task.delay(
        user_id=user.id,
        ip_address=ip,
        user_agent=ua
    )