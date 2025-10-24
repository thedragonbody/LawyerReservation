from urllib.parse import quote_plus

from django.db import models
from users.models import User

def avatar_upload_path(instance, filename):
    return f"lawyer_avatars/{instance.user.id}/{filename}"

def document_upload_path(instance, filename):
    return f"lawyer_docs/{instance.user.id}/{filename}"

class LawyerProfile(models.Model):
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('busy', 'Busy'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lawyer_profile')

    # اطلاعات حرفه‌ای
    expertise = models.CharField(max_length=200, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    degree = models.CharField(max_length=200, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    
    # وضعیت آنلاین
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline')

    # مدارک و بایو
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)

    # اطلاعات دفتر
    office_address = models.CharField(max_length=250, blank=True, null=True)
    office_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    office_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # پروانه و منطقه فعالیت
    license_number = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # زمان ایجاد و آپدیت
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ========================
    # property‌ها و متدهای کمکی
    # ========================
    @property
    def is_online(self):
        return self.status == 'online'

    @property
    def is_offline(self):
        return self.status == 'offline'

    def get_office_location(self):
        latitude = float(self.office_latitude) if self.office_latitude is not None else None
        longitude = float(self.office_longitude) if self.office_longitude is not None else None
        address = self.office_address

        map_query = None
        if latitude is not None and longitude is not None:
            map_query = f"{latitude},{longitude}"
        elif address:
            map_query = address

        map_url = None
        map_embed_url = None
        if map_query:
            encoded_query = quote_plus(str(map_query))
            map_url = f"https://www.google.com/maps/search/?api=1&query={encoded_query}"
            map_embed_url = f"https://maps.google.com/maps?q={encoded_query}&output=embed"

        return {
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
            "map_url": map_url,
            "map_embed_url": map_embed_url,
        }

    def full_profile(self):
        return {
            "name": self.user.get_full_name(),
            "phone": self.user.phone_number,
            "expertise": self.expertise,
            "specialization": self.specialization,
            "degree": self.degree,
            "experience_years": self.experience_years,
            "status": self.status,
            "license_number": self.license_number,
            "office": self.get_office_location(),
            "city": self.city,
            "region": self.region,
            "avatar": self.avatar.url if self.avatar else None,
            "bio": self.bio,
        }

    def __str__(self):
        return f"{self.user.get_full_name()} | {self.expertise}"