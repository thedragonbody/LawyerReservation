from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from users.models import User


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    reserved_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Wallet<{self.user_id}>"

    @property
    def available_balance(self) -> Decimal:
        return self.balance - self.reserved_balance


class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        RESERVE = "reserve", "Reserve"
        RELEASE = "release", "Release"
        DEBIT = "debit", "Debit"
        REFUND = "refund", "Refund"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    payment = models.ForeignKey(
        "Payment",
        on_delete=models.CASCADE,
        related_name="wallet_transactions",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"WalletTransaction<{self.id}> {self.type} {self.amount}"

class Payment(models.Model):
    """
    مدل پرداخت که هم برای OnlineAppointments و هم Subscription کاربرد داره.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    class Method(models.TextChoices):
        IDPAY = "idpay", "IDPay"
        ZARINPAL = "zarinpal", "Zarinpal"
        WALLET = "wallet", "Wallet"

    # 🔹 پرداخت مرتبط با کاربر
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.IDPAY,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    provider_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    wallet_reserved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

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
    inperson_appointment = models.ForeignKey(
        "appointments.InPersonAppointment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payments",
    )

    def __str__(self):
        if self.appointment:
            related = "OnlineAppointment"
        elif self.inperson_appointment:
            related = "InPersonAppointment"
        elif self.subscription:
            related = "Subscription"
        else:
            related = "General"
        return (
            f"Payment {self.id} | {self.user.get_full_name()} | "
            f"{self.amount} | {related} | {self.status}"
        )

    def mark_completed(self, provider_data=None):
        if self.status == self.Status.COMPLETED:
            return

        if self.payment_method == self.Method.WALLET:
            from payments.utils import capture_wallet_payment

            capture_wallet_payment(self)

        self.status = self.Status.COMPLETED
        update_fields = ["status", "updated_at"]
        if provider_data is not None:
            self.provider_data = provider_data
            update_fields.append("provider_data")
        self.save(update_fields=update_fields)

        # --- فعالسازی appointment
        if self.appointment:
            # اطمینان از اینکه appointments.models import شده
            # یا اینکه متد confirm در خود مدل appointment تعریف شده
            self.appointment.confirm()

        if self.inperson_appointment:
            self.inperson_appointment.mark_payment_completed()

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
        if self.payment_method == self.Method.WALLET:
            from payments.utils import release_wallet_reservation

            release_wallet_reservation(self)

        self.status = self.Status.FAILED
        self.save(update_fields=["status", "updated_at"])

    def mark_refunded(self):
        if self.status != self.Status.COMPLETED:
            return

        if self.payment_method == self.Method.WALLET:
            from payments.utils import refund_wallet_payment

            refund_wallet_payment(self)

        self.status = self.Status.REFUNDED
        self.save(update_fields=["status", "updated_at"])

        if self.appointment:
            # TODO: align with appointment cancellation workflow
            pass
        if self.inperson_appointment:
            self.inperson_appointment.mark_payment_refunded()
        if self.subscription:
            self.subscription.active = False
            self.subscription.save(update_fields=["active"])