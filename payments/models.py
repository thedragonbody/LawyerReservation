from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal

from common.models import BaseModel
from users.models import User
from appointments.models import Appointment


class Payment(BaseModel):
    """
    مدل پرداخت که هم پرداخت‌های مرتبط با قرار ملاقات (Appointment)
    و هم پرداخت‌های مربوط به اشتراک (Subscription) را پوشش می‌دهد.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')

    # 🔹 استفاده از string reference برای جلوگیری از circular import با ai_assistant
    subscription = models.ForeignKey(
        "ai_assistant.Subscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text=_("در صورت پرداخت برای اشتراک، این فیلد پر می‌شود."),
    )

    METHOD_CHOICES = [
        ("idpay", "IDPay"),
        ("zarinpal", "Zarinpal"),
    ]

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True,
        help_text=_("در صورت پرداخت برای قرار ملاقات، این فیلد پر می‌شود."),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="idpay")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    provider_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # -----------------------------
    # ✅ متدهای کاربردی پرداخت
    # -----------------------------

    def __str__(self):
        related = "Appointment" if self.appointment else "Subscription"
        return f"Payment {self.id} | {self.user.email} | {self.amount} | {related} | {self.status}"

    def mark_completed(self, provider_data=None):
        """
        به‌روزرسانی وضعیت پرداخت به COMPLETED
        و فعال‌سازی سرویس مرتبط (Appointment یا Subscription)
        """
        if self.status == Payment.Status.COMPLETED:
            return  # از چندبار ذخیره جلوگیری می‌کنیم

        self.status = Payment.Status.COMPLETED
        if provider_data:
            self.provider_data = provider_data
        self.save(update_fields=["status", "provider_data", "updated_at"])

        # 🔹 در صورتی که پرداخت برای یک قرار ملاقات باشد
        if self.appointment:
            try:
                # تلاش برای confirm با transaction_id (پشتیبانی از هر دو حالت)
                self.appointment.confirm(transaction_id=self.transaction_id)
            except TypeError:
                try:
                    self.appointment.confirm()
                except Exception:
                    pass

        # 🔹 در صورتی که پرداخت برای اشتراک باشد
        if self.subscription:
            sub = self.subscription
            sub.active = True
            if hasattr(sub, "duration_days") and sub.duration_days:
                sub.ends_at = timezone.now() + timezone.timedelta(days=sub.duration_days)
            else:
                sub.ends_at = timezone.now() + timezone.timedelta(days=30)
            sub.save(update_fields=["active", "ends_at"])

    def mark_failed(self, reason=None):
        """
        علامت‌گذاری پرداخت به عنوان ناموفق.
        """
        self.status = Payment.Status.FAILED
        self.save(update_fields=["status", "updated_at"])
        if reason:
            # لاگ برای مانیتورینگ
            from ai_assistant.models import AIErrorLog
            AIErrorLog.objects.create(user=self.user, question="PAYMENT FAILED", error=str(reason))

    def mark_refunded(self):
        """
        بازپرداخت (Refund) پرداخت تکمیل‌شده.
        در صورت وجود قرار ملاقات، آن را لغو می‌کند.
        """
        if self.status != Payment.Status.COMPLETED:
            return

        self.status = Payment.Status.REFUNDED
        self.save(update_fields=["status", "updated_at"])

        # 🔹 لغو قرار ملاقات در صورت وجود
        if self.appointment:
            try:
                self.appointment.cancel(cancellation_reason="Refunded by system", refund=True)
            except TypeError:
                try:
                    self.appointment.cancel()
                except Exception:
                    pass

        # 🔹 غیرفعال کردن اشتراک در صورت وجود
        if self.subscription:
            self.subscription.active = False
            self.subscription.save(update_fields=["active"])

