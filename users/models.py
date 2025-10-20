from django.db import models, transaction
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from datetime import timedelta
import random
from django.utils.translation import gettext_lazy as _
from geopy.geocoders import Nominatim
from django.contrib.auth import get_user_model
from django.conf import settings


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
        ('signup', 'Signup'),
        ('reset', 'Password Reset'),
        ('phone_verify', 'Phone Verification'),
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