from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from .models import User
from .documents import UserDocument
from django.contrib.auth.signals import user_logged_in
from client_profile.models import ClientProfile, Device

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

@receiver(user_logged_in)
def on_user_logged_in(sender, user, request, **kwargs):
    cp = getattr(user, 'client_profile', None)
    if not cp:
        return
    ip = request.META.get('REMOTE_ADDR')
    ua = request.META.get('HTTP_USER_AGENT', '')[:500]
    name = ua.split(')')[-1].strip() if ua else ''
    Device.objects.update_or_create(
        client=cp,
        ip_address=ip,
        user_agent=ua,
        defaults={'name': name, 'revoked': False}
    )
    # update last login fields
    cp.last_login_ip = ip
    cp.last_login_user_agent = ua
    cp.save(update_fields=['last_login_ip','last_login_user_agent'])