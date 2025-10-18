from django.db import models
from users.models import User

class LawyerProfile(models.Model):
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('busy', 'Busy'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lawyer_profile')
    expertise = models.CharField(max_length=200, blank=True)
    degree = models.CharField(max_length=200, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline')
    document = models.FileField(upload_to='lawyer_docs/', blank=True, null=True)
    bio = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='lawyer_avatars/', blank=True, null=True)
    office_address = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_office_location(self):
        # میتونی مختصات GPS یا یک dictionary برگردونی
        return {"address": self.office_address}

    def __str__(self):
        return f"{self.user.phone_number}"