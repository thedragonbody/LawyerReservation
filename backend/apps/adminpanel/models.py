from django.db import models
from django.conf import settings
import uuid


class CommissionSetting(models.Model):
    title = models.CharField(max_length=120, default='کمیسیون پیش‌فرض')
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=9)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_commission_settings'

    def __str__(self):
        return f'{self.title} - {self.commission_percent}%'


class DiscountCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    percent = models.PositiveIntegerField(default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=0)
    used_count = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_discount_codes'
        ordering = ['-created_at']

    def __str__(self):
        return self.code


class LawyerSettlement(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('paid', 'پرداخت شده'),
        ('hold', 'متوقف'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lawyer = models.ForeignKey('lawyers.LawyerProfile', on_delete=models.CASCADE, related_name='settlements')
    amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    note = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_lawyer_settlements'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.lawyer_id} - {self.net_amount}'


class SiteContent(models.Model):
    key = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_site_content'
        ordering = ['key']

    def __str__(self):
        return self.key
