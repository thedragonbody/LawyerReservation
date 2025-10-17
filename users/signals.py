from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from .models import User, ClientProfile, LawyerProfile
from .documents import UserDocument, ClientProfileDocument, LawyerProfileDocument

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


# ===================== ClientProfile =====================
@receiver(post_save, sender=ClientProfile)
def update_client_document(sender, instance, **kwargs):
    """
    Create or update ClientProfile document in Elasticsearch atomically.
    """
    def _update():
        doc = ClientProfileDocument(
            meta={'id': instance.id},
            user_id=str(instance.user.id),
            phone_number=instance.user.phone_number,
            national_id=instance.national_id,
            avatar=instance.avatar.url if instance.avatar else '',
            created_at=instance.created_at,
            updated_at=instance.updated_at
        )
        doc.save()
    transaction.on_commit(_update)


@receiver(pre_delete, sender=ClientProfile)
def delete_client_document(sender, instance, **kwargs):
    try:
        doc = ClientProfileDocument.get(id=instance.id)
        doc.delete()
    except Exception:
        pass


# ===================== LawyerProfile =====================
@receiver(post_save, sender=LawyerProfile)
def update_lawyer_document(sender, instance, **kwargs):
    """
    Create or update LawyerProfile document in Elasticsearch atomically.
    """
    def _update():
        doc = LawyerProfileDocument(
            meta={'id': instance.id},
            user_id=str(instance.user.id),
            phone_number=instance.user.phone_number,
            degree=instance.degree,
            experience_years=instance.experience_years,
            expertise=instance.expertise,
            status=instance.status,
            bio=instance.bio,
            city=instance.city,
            specialization=instance.specialization,
            avatar=instance.avatar.url if instance.avatar else '',
            created_at=instance.created_at,
            updated_at=instance.updated_at
        )
        doc.save()
    transaction.on_commit(_update)


@receiver(pre_delete, sender=LawyerProfile)
def delete_lawyer_document(sender, instance, **kwargs):
    try:
        doc = LawyerProfileDocument.get(id=instance.id)
        doc.delete()
    except Exception:
        pass