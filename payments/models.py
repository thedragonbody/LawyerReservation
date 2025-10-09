from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models import BaseModel
from users.models import User
from appointments.models import Appointment
from django.utils import timezone
from decimal import Decimal
from ai_assistant.models import Subscription

class Payment(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    METHOD_CHOICES = [
        ("idpay", "IDPay"),
        ("zarinpal", "Zarinpal"),
    ]

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="idpay")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    provider_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} | {self.user.email} | {self.amount} | {self.status}"

    def mark_completed(self, provider_data=None):
        if self.status != Payment.Status.COMPLETED:
            self.status = Payment.Status.COMPLETED
            if provider_data:
                self.provider_data = provider_data
            self.save(update_fields=["status", "provider_data"])
            self.appointment.confirm(self)

    def mark_refunded(self):
        if self.status == Payment.Status.COMPLETED:
            self.status = Payment.Status.REFUNDED
            self.save(update_fields=["status"])
            self.appointment.cancel(refunded=True)