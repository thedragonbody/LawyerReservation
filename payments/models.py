from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from users.models import User
from common.models import BaseModel
from notifications.models import Notification
from notifications.utils import send_sms


class Payment(BaseModel):
    """
    💳 مدل پرداخت برای:
    ✅ OnlineAppointment
    ✅ Subscription
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار پرداخت")
        COMPLETED = "completed", _("پرداخت تکمیل شده")
        FAILED = "failed", _("پرداخت ناموفق")
        REFUNDED = "refunded", _("بازپرداخت شده")

    METHOD_CHOICES = [
        ("idpay", "IDPay"),
        ("zarinpal", "Zarinpal"),
        ("simulation", "Simulation"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("کاربر"),
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("مبلغ پرداخت"),
    )

    payment_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default="simulation",
        verbose_name=_("روش پرداخت"),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("وضعیت"),
    )

    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("کد تراکنش"),
    )

    provider_data = models.JSONField(blank=True, null=True)

    # -------------------------------
    # روابط اصلی
    # -------------------------------
    online_appointment = models.OneToOneField(
        "appointments.OnlineAppointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment",
        verbose_name=_("رزرو آنلاین"),
    )

    subscription = models.ForeignKey(
        "ai_assistant.Subscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name=_("اشتراک هوش مصنوعی"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ----------------------------------------------------
    # ✅ متدهای عملیاتی پرداخت
    # ----------------------------------------------------

    def __str__(self):
        target = (
            "OnlineAppointment" if self.online_appointment
            else "Subscription" if self.subscription
            else "Unknown"
        )
        return f"Payment {self.id} | {self.user.email} | {self.amount} | {target} | {self.status}"

    def mark_completed(self, provider_data=None):
        """تکمیل پرداخت و فعال‌سازی سرویس"""
        if self.status == self.Status.COMPLETED:
            return

        with transaction.atomic():
            self.status = self.Status.COMPLETED
            if provider_data:
                self.provider_data = provider_data
            self.save(update_fields=["status", "provider_data", "updated_at"])

            # ✅ اگر مربوط به رزرو آنلاین است
            if self.online_appointment:
                self.online_appointment.confirm_and_create_meet_link()

            # ✅ اگر مربوط به اشتراک است
            elif self.subscription:
                self.subscription.active = True
                self.subscription.ends_at = timezone.now() + timezone.timedelta(days=30)
                self.subscription.save(update_fields=["active", "ends_at"])
        if self.appointment or self.online_appointment:
            appointment = getattr(self, "appointment", None) or getattr(self, "online_appointment", None)
            client_user = appointment.client.user
            lawyer_user = appointment.lawyer.user
            meet_link = getattr(appointment, "meet_link", None)
            start_time = appointment.start_time.strftime("%Y-%m-%d %H:%M")

            # --- برای کلاینت
            Notification.send(
                user=client_user,
                title="رزرو شما تأیید شد ✅",
                message=f"رزرو شما برای {start_time} تأیید شد.\nلینک جلسه: {meet_link}",
                type_=Notification.Type.APPOINTMENT_CONFIRMED,
            )
            send_sms(client_user.phone_number, f"رزرو شما در تاریخ {start_time} تأیید شد ✅")

            # --- برای وکیل
            Notification.send(
                user=lawyer_user,
                title="جلسه جدید رزرو شد 📅",
                message=f"کاربر {client_user.get_full_name()} جلسه‌ای برای {start_time} رزرو کرده است.",
                type_=Notification.Type.APPOINTMENT_REMINDER,
            )
            send_sms(lawyer_user.phone_number, f"جلسه جدید با {client_user.get_full_name()} در {start_time}")
            def mark_failed(self, reason=None):
                """پرداخت ناموفق"""
                self.status = self.Status.FAILED
                self.save(update_fields=["status", "updated_at"])
                if reason:
                    print(f"[Payment] Failed for {self.user.email} → {reason}")

    def mark_refunded(self):
        """بازپرداخت پرداخت تکمیل‌شده"""
        if self.status != self.Status.COMPLETED:
            return

        with transaction.atomic():
            self.status = self.Status.REFUNDED
            self.save(update_fields=["status", "updated_at"])

            if self.online_appointment:
                self.online_appointment.cancel(reason="Refunded by system")

            elif self.subscription:
                self.subscription.active = False
                self.subscription.save(update_fields=["active"])