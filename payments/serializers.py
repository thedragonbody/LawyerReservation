from decimal import Decimal

from rest_framework import serializers

from ai_assistant.models import Subscription
from appointments.models import OnlineAppointment

from payments.models import Payment, Wallet
from payments import utils as payment_utils


class PaymentSerializer(serializers.ModelSerializer):
    appointment_id = serializers.PrimaryKeyRelatedField(
        source="appointment",
        queryset=OnlineAppointment.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    subscription_id = serializers.PrimaryKeyRelatedField(
        source="subscription",
        queryset=Subscription.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "amount",
            "status",
            "payment_method",
            "transaction_id",
            "appointment_id",
            "subscription_id",
            "wallet_reserved_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "transaction_id",
            "wallet_reserved_amount",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "user": {"read_only": True},
        }

    def validate_amount(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class WalletSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        source="available_balance",
    )

    class Meta:
        model = Wallet
        fields = ["balance", "reserved_balance", "available_balance", "updated_at"]
        read_only_fields = fields


class WalletTopUpSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def save(self, **kwargs):
        request = self.context["request"]
        wallet = payment_utils.increase_wallet_balance(
            user=request.user,
            amount=self.validated_data["amount"],
            description=self.validated_data.get("description", ""),
        )
        return wallet


class WalletReserveSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )

    def validate(self, attrs):
        payment_id = attrs.get("payment_id")
        request = self.context["request"]

        try:
            payment = Payment.objects.get(id=payment_id, user=request.user)
        except Payment.DoesNotExist as exc:
            raise serializers.ValidationError({"payment_id": "Payment not found."}) from exc

        if payment.payment_method != Payment.Method.WALLET:
            raise serializers.ValidationError({"payment_id": "Selected payment is not a wallet payment."})
        if payment.status != Payment.Status.PENDING:
            raise serializers.ValidationError({"payment_id": "Only pending payments can reserve funds."})
        if payment.wallet_reserved_amount > 0:
            raise serializers.ValidationError({"payment_id": "Wallet already reserved for this payment."})

        amount = attrs.get("amount") or payment.amount
        if amount <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero."})

        attrs["payment"] = payment
        attrs["amount"] = amount
        return attrs

    def save(self, **kwargs):
        payment: Payment = self.validated_data["payment"]
        amount: Decimal = self.validated_data["amount"]
        if payment.amount != amount:
            payment.amount = amount
            payment.save(update_fields=["amount"])
        wallet = payment_utils.reserve_wallet_funds(payment=payment, amount=amount)
        payment.refresh_from_db(fields=["wallet_reserved_amount"])
        return payment, wallet
