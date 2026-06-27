from django.db import models
from django.utils import timezone
import random
import string


class OTPRecord(models.Model):
    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=10)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'otp_records'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.phone} — {self.code}'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired and self.attempts < 5
