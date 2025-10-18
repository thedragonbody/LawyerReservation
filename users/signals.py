from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from .models import User
from .documents import UserDocument

# ===================== User =====================
@receiver(post_save, sender=User)
def update_user_document(sender, instance, **kwargs):
    """
    Create or update User document in Elasticsearch atomically.
    """
    def _update():
        doc = UserDocument(
            meta={'id': instance.id},
            phone_number=instance.phone_number,
            first_name=instance.first_name,
            last_name=instance.last_name,
            full_name=f"{instance.first_name or ''} {instance.last_name or ''}".strip(),
            is_active=str(instance.is_active),
            date_joined=instance.date_joined
        )
        doc.save()
    transaction.on_commit(_update)


@receiver(pre_delete, sender=User)
def delete_user_document(sender, instance, **kwargs):
    try:
        doc = UserDocument.get(id=instance.id)
        doc.delete()
    except Exception:
        pass

