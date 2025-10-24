from datetime import timedelta
import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import BaseUserManager, PermissionsMixin, AbstractBaseUser
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.fields import EncryptedTextField

# ================= Custom User =================
class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('شماره تلفن باید مشخص شود')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    def __str__(self):
        return str(self.phone_number)

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.phone_number

    def get_short_name(self):
        return self.first_name or self.phone_number


# ================= PasswordResetCode =================
class PasswordResetCode(models.Model):
    PURPOSE_CHOICES = [
        ("login", "Passwordless Login"),
        ("signup", "Signup"),
        ("reset", "Password Reset"),
        ("phone_verify", "Phone Verification"),
    ]

    phone_number = models.CharField(max_length=15, db_index=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['phone_number', 'purpose']),
        ]
        ordering = ['-created_at']

    @classmethod
    def generate_code(cls, phone_number, purpose):
        code = f"{random.randint(100000, 999999)}"
        cls.objects.create(phone_number=phone_number, code=code, purpose=purpose)
        # اینجا می‌تونی تابع ارسال SMS قرار بدی
        print(f"[OTP] Sent {code} for {purpose} to {phone_number}")
        return code

    @classmethod
    def verify_code(cls, phone_number, code, purpose, max_attempts=5, ttl_minutes=5):
        """بررسی OTP با محدودیت زمانی و تلاش"""
        try:
            with transaction.atomic():
                otp = cls.objects.select_for_update().filter(
                    phone_number=phone_number,
                    purpose=purpose,
                    is_used=False
                ).latest('created_at')
                otp.attempts += 1
                otp.save(update_fields=['attempts'])
                if otp.attempts > max_attempts:
                    raise ValueError("کد بیش از حد تلاش شده است. لطفاً دوباره درخواست دهید.")
                if (timezone.now() - otp.created_at) > timedelta(minutes=ttl_minutes):
                    raise ValueError("کد منقضی شده است.")
                if otp.code != code:
                    raise ValueError("کد نادرست است.")
                otp.is_used = True
                otp.save(update_fields=['is_used'])
                return True
        except cls.DoesNotExist:
            raise ValueError("کد معتبر یافت نشد.")


class OAuthToken(models.Model):
    """OAuth tokens stored per user and provider for calendar integrations."""

    PROVIDER_CHOICES = (
        ("google", "Google"),
        ("microsoft", "Microsoft"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="oauth_tokens")
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default="google")
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField(blank=True, null=True)
    scope = models.CharField(max_length=255, blank=True)
    token_type = models.CharField(max_length=50, blank=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "provider")
        ordering = ("user", "provider")

    def __str__(self):
        return f"{self.user_id} | {self.provider}"

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())

    def mark_refreshed(
        self,
        expires_in=None,
        access_token=None,
        refresh_token=None,
        scope=None,
        token_type=None,
        expires_at=None,
    ):
        if access_token is not None:
            self.access_token = access_token
        if refresh_token is not None:
            self.refresh_token = refresh_token
        if scope is not None:
            self.scope = scope
        if token_type is not None:
            self.token_type = token_type
        if expires_in is not None:
            self.expires_at = timezone.now() + timedelta(seconds=expires_in)
        elif expires_at is not None:
            self.expires_at = expires_at
        self.save()
        
