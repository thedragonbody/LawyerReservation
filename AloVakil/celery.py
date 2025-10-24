import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AloVakil.settings")

app = Celery("AloVakil")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-reminders-every-5-min": {
        "task": "appointments.tasks.send_appointment_reminders_task",
        "schedule": 300,  # هر 5 دقیقه
    },
    "refresh-oauth-tokens": {
        "task": "appointments.tasks.refresh_expiring_oauth_tokens",
        "schedule": 600,  # هر 10 دقیقه
    },
}

from celery import shared_task

@shared_task
def send_sms_task(phone_number, message):
    # فقط print فعلا، بعدا سرویس واقعی
    print(f"[SMS] To: {phone_number} | Message: {message}")