from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
import logging

# 💡 NEW: Import Celery tasks
from searchs.tasks import index_instance_task, delete_instance_task

logger = logging.getLogger("searchs")

# ---------------------- Document Mapping Helper ----------------------
# استفاده از این دیکشنری برای ارسال نام کلاس به Celery Task
DOCUMENT_MAP = {
    'User': 'UserDocument',
    'LawyerProfile': 'LawyerProfileDocument',
    'ClientProfile': 'ClientProfileDocument',
    'OnlineAppointment': 'AppointmentDocument',
    'Payment': 'PaymentDocument',
    'Case': 'CaseDocument',
}


# ---------------------- Post Save Signal ----------------------
def handle_post_save(sender, instance, **kwargs):
    model_name = sender.__name__
    doc_class_name = DOCUMENT_MAP.get(model_name)
    
    if doc_class_name:
        # 🚀 NEW: اجرای وظیفه نمایه سازی در Celery در پس‌زمینه
        # این فراخوانی غیرهمزمان است و بلافاصله برمی‌گردد.
        index_instance_task.delay(sender._meta.app_label, model_name, instance.id)
    else:
        logger.warning(f"No document map found for model: {model_name}")

# ---------------------- Post Delete Signal ----------------------
def handle_post_delete(sender, instance, **kwargs):
    model_name = sender.__name__
    doc_class_name = DOCUMENT_MAP.get(model_name)
    
    if doc_class_name:
        # 🚀 NEW: اجرای وظیفه حذف در Celery در پس‌زمینه
        delete_instance_task.delay(doc_class_name, instance.id)
    else:
        logger.warning(f"No document map found for model: {model_name}")

# ---------------------- Register Receivers ----------------------

MODELS_TO_INDEX = [
    apps.get_model('users', 'User'),
    apps.get_model('lawyer_profile', 'LawyerProfile'),
    apps.get_model('client_profile', 'ClientProfile'),
    apps.get_model('appointments', 'OnlineAppointment'),
    apps.get_model('payments', 'Payment'),
    apps.get_model('cases', 'Case'),
]

for Model in MODELS_TO_INDEX:
    post_save.connect(handle_post_save, sender=Model)
    post_delete.connect(handle_post_delete, sender=Model)