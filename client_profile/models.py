from django.db import models
from users.models import User
from django.utils import timezone
import uuid

def client_avatar_path(instance, filename):
    return f"client_avatars/{instance.user.id}/{filename}"

class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    national_id = models.CharField(max_length=50, blank=True, null=True)
    avatar = models.ImageField(upload_to=client_avatar_path, blank=True, null=True)

    # === Verification & Security ===
    is_phone_verified = models.BooleanField(default=False)
    phone_verification_code = models.CharField(max_length=6, blank=True, null=True)
    phone_verification_sent_at = models.DateTimeField(blank=True, null=True)

    # Favorite lawyers
    favorites = models.ManyToManyField('lawyer_profile.LawyerProfile', related_name='favorited_by', blank=True)

    # Device / login tracking aggregated info (optional fields)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_login_user_agent = models.CharField(max_length=512, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_phone_code(self):
        # generate 6-digit code
        code = str(uuid.uuid4().int)[:6]
        self.phone_verification_code = code
        self.phone_verification_sent_at = timezone.now()
        self.save(update_fields=['phone_verification_code','phone_verification_sent_at'])
        return code

    def mark_phone_verified(self):
        self.is_phone_verified = True
        self.phone_verification_code = None
        self.save(update_fields=['is_phone_verified','phone_verification_code'])

    def __str__(self):
        return f"{self.user.phone_number}"
    
class Device(models.Model):
    """
    ثبت دستگاه‌ها و sessionها برای امنیت و قابلیت revoke
    """
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='devices')
    name = models.CharField(max_length=200, blank=True, null=True)  # Eg: "Chrome on Windows"
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=512, blank=True, null=True)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.client.user.phone_number} | {self.name or self.ip_address}"