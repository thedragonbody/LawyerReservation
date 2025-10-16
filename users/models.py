from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
import random
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta

# ================= Custom UserManager =================
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("The phone number must be set")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)  # سوپر یوزر همیشه تایید شده

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        
        return self.create_user(phone_number, password, **extra_fields)


# ---------------- User Model ----------------
class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    device_token = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)  # تایید شماره موبایل
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.phone_number})"

    def generate_otp(self):
        self.otp_code = f"{random.randint(100000, 999999)}"
        self.otp_created_at = timezone.now()
        self.save()
        return self.otp_code

    def verify_otp(self, code):
        if self.otp_code == code and self.otp_created_at:
            # اعتبار OTP: 5 دقیقه
            diff = timezone.now() - self.otp_created_at
            if diff.total_seconds() <= 300:
                self.is_verified = True
                self.otp_code = None
                self.otp_created_at = None
                self.save()
                return True
        return False


# ================= ClientProfile =================
class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    national_id = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    avatar = models.ImageField(upload_to='avatars/clients/', blank=True, null=True)


# ================= LawyerProfile =================
class LawyerProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lawyer_profile')
    expertise = models.TextField(blank=True)
    degree = models.CharField(max_length=255, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    document = models.FileField(upload_to='lawyer_docs/', blank=True, null=True)
    bio = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    avatar = models.ImageField(upload_to='avatars/lawyers/', blank=True, null=True)


class PasswordResetCode(models.Model):
    phone_number = models.CharField(max_length=15)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        """کد فقط 2 دقیقه اعتبار دارد و استفاده نشده باشد"""
        return not self.is_used and (timezone.now() - self.created_at < timedelta(minutes=2))

    @staticmethod
    def generate_code(phone_number):
        """کد ۶ رقمی و ذخیره در دیتابیس"""
        code = str(random.randint(100000, 999999))
        obj = PasswordResetCode.objects.create(phone_number=phone_number, code=code)
        return obj