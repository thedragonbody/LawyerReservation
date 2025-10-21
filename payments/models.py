from django.db import models
from django.utils import timezone
from decimal import Decimal
from users.models import User

class Payment(models.Model):
    """
    مدل پرداخت که هم برای OnlineAppointments و هم Subscription کاربرد داره.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    METHOD_CHOICES = [
        ("idpay", "IDPay"),
        ("zarinpal", "Zarinpal"),
    ]

    # 🔹 پرداخت مرتبط با کاربر
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="idpay")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    provider_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- روابط به صورت string reference برای جلوگیری از circular import
    appointment = models.ForeignKey(
        "appointments.OnlineAppointment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payments",
    )
    subscription = models.ForeignKey(
        "ai_assistant.Subscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    def __str__(self):
        related = "Appointment" if self.appointment else "Subscription"
        return f"Payment {self.id} | {self.user.email} | {self.amount} | {related} | {self.status}"

    def mark_completed(self, provider_data=None):
        if self.status == self.Status.COMPLETED:
            return

        self.status = self.Status.COMPLETED
        if provider_data:
            self.provider_data = provider_data
        self.save(update_fields=["status", "provider_data", "updated_at"])

        # --- فعالسازی appointment
        if self.appointment:
            # اطمینان از اینکه appointments.models import شده
            # یا اینکه متد confirm در خود مدل appointment تعریف شده
            self.appointment.confirm(transaction_id=self.transaction_id)

        # --- فعالسازی subscription
        if self.subscription:
            self.subscription.active = True
            
            # 💡 رفع باگ: duration_days از 'plan' خوانده شود نه خود 'subscription'
            duration = 30 # پیش‌فرض
            if self.subscription.plan:
                duration = getattr(self.subscription.plan, "duration_days", 30)
            
            self.subscription.ends_at = timezone.now() + timezone.timedelta(days=duration)
            self.subscription.save(update_fields=["active", "ends_at"])

    def mark_failed(self):
        self.status = self.Status.FAILED
        self.save(update_fields=["status", "updated_at"])

    def mark_refunded(self):
        if self.status != self.Status.COMPLETED:
            return
        self.status = self.Status.REFUNDED
        self.save(update_fields=["status", "updated_at"])

        if self.appointment:
            self.appointment.cancel(cancellation_reason="Refunded by system", refund=True)
        if self.subscription:
            self.subscription.active = False
            self.subscription.save(update_fields=["active"])