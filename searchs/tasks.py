from celery import shared_task
from django.apps import apps
import logging

logger = logging.getLogger("celery")

@shared_task
def index_instance_task(app_label: str, model_name: str, instance_id: int):
    """
    وظیفه Celery برای نمایه سازی یک آبجکت جدید یا به‌روز شده در Elasticsearch.
    """
    try:
        Model = apps.get_model(app_label, model_name)
        instance = Model.objects.get(id=instance_id)
        
        # 1. پیدا کردن Document Class مربوطه
        document_map = {
            'users': 'UserDocument',
            'lawyer_profile': 'LawyerProfileDocument',
            'client_profile': 'ClientProfileDocument',
            'appointments': 'AppointmentDocument',
            'payments': 'PaymentDocument',
            'cases': 'CaseDocument',
        }
        
        # فرض می‌کنیم Document Classها در searchs.documents وجود دارند
        from searchs.documents import (
            UserDocument, LawyerProfileDocument, ClientProfileDocument,
            AppointmentDocument, PaymentDocument, CaseDocument
        )
        doc_classes = {
            'UserDocument': UserDocument,
            'LawyerProfileDocument': LawyerProfileDocument,
            'ClientProfileDocument': ClientProfileDocument,
            'AppointmentDocument': AppointmentDocument,
            'PaymentDocument': PaymentDocument,
            'CaseDocument': CaseDocument,
        }
        
        doc_class_name = document_map.get(app_label) # از app_label به عنوان کلید استفاده می‌کنیم
        if not doc_class_name:
            logger.warning(f"No document map for app_label: {app_label}")
            return

        DocClass = doc_classes.get(doc_class_name.replace('Document', Model.__name__ + 'Document', 1) if Model.__name__ + 'Document' in doc_classes else doc_classes[doc_class_name])
        
        if not DocClass:
             logger.warning(f"No DocClass found for {app_label}.{model_name}")
             return

        # 2. نمایه سازی
        doc = DocClass.from_instance(instance)
        doc.save()
        logger.info(f"Successfully indexed {DocClass.__name__} ID: {instance_id}")

    except Model.DoesNotExist:
        logger.warning(f"Instance {model_name} ID {instance_id} not found for indexing.")
    except Exception as e:
        logger.error(f"Failed to index {model_name} ID {instance_id}: {e}")

@shared_task
def delete_instance_task(doc_class_name: str, instance_id: int):
    """
    وظیفه Celery برای حذف یک سند از Elasticsearch.
    """
    try:
        from searchs.documents import (
            UserDocument, LawyerProfileDocument, ClientProfileDocument,
            AppointmentDocument, PaymentDocument, CaseDocument
        )
        doc_classes = {
            'UserDocument': UserDocument,
            'LawyerProfileDocument': LawyerProfileDocument,
            'ClientProfileDocument': ClientProfileDocument,
            'AppointmentDocument': AppointmentDocument,
            'PaymentDocument': PaymentDocument,
            'CaseDocument': CaseDocument,
        }

        DocClass = doc_classes.get(doc_class_name)
        if not DocClass:
            logger.warning(f"DocClass {doc_class_name} not found for deletion.")
            return

        doc = DocClass(meta={'id': instance_id})
        doc.delete()
        logger.info(f"Successfully deleted {doc_class_name} ID: {instance_id}")

    except Exception as e:
        logger.error(f"Failed to delete {doc_class_name} ID {instance_id}: {e}")