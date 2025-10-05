from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

# ================= Custom UserManager =================
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, phone_number, first_name='', last_name='', password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be set')
        if not phone_number:
            raise ValueError('Phone number must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, phone_number=phone_number,
                          first_name=first_name, last_name=last_name,
                          **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone_number, first_name='', last_name='', password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, phone_number, first_name, last_name, password, **extra_fields)


# ================= User =================
class User(AbstractUser):
    username = None  # حذف username
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number', 'first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


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