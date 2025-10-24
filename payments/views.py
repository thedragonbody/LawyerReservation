from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from payments.models import Payment, Wallet
from appointments.models import OnlineAppointment
from payments.serializers import (
    PaymentSerializer,
    WalletReserveSerializer,
    WalletSerializer,
    WalletTopUpSerializer,
)
from payments import utils as payment_utils


class CreatePaymentView(generics.CreateAPIView):
    """
    کاربر رزرو آنلاین انجام داده → درخواست پرداخت ایجاد می‌کند.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def post(self, request, *args, **kwargs):
        appointment_id = request.data.get("appointment_id")
        amount = request.data.get("amount")

        if not appointment_id or not amount:
            return Response({"error": "Missing appointment_id or amount"}, status=400)

        try:
            appointment = OnlineAppointment.objects.get(
                id=appointment_id, client__user=request.user
            )
        except OnlineAppointment.DoesNotExist:
            return Response({"error": "Appointment not found or unauthorized"}, status=404)

        # جلوگیری از ایجاد پرداخت تکراری
        if appointment.payments.filter(status=Payment.Status.COMPLETED).exists():
            return Response({"detail": "Payment already completed for this appointment."}, status=400)

        payment_method = request.data.get("payment_method", Payment.Method.IDPAY)
        if payment_method not in Payment.Method.values:
            return Response({"detail": "Invalid payment method."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount_decimal = Decimal(str(amount))
        except Exception:
            return Response({"detail": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST)

        provider_response = None

        with transaction.atomic():
            payment = Payment.objects.create(
                user=request.user,
                appointment=appointment,
                amount=amount_decimal,
                payment_method=payment_method,
            )

            if payment_method == Payment.Method.WALLET:
                try:
                    payment_utils.reserve_wallet_funds(payment=payment)
                except ValidationError as exc:
                    transaction.set_rollback(True)
                    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            if payment_method == Payment.Method.IDPAY:
                callback_url = getattr(settings, "IDPAY_CALLBACK_URL", None)
                if not callback_url:
                    callback_url = request.build_absolute_uri(reverse("payments:payment-verify"))

                order_id = str(payment.id)
                multiplier = getattr(settings, "PAYMENT_AMOUNT_MULTIPLIER", 1)
                amount_to_pay = int(payment.amount * multiplier)

                try:
                    provider_response = payment_utils.create_payment_request(
                        order_id=order_id,
                        amount=amount_to_pay,
                        callback=callback_url,
                    )
                except Exception:
                    transaction.set_rollback(True)
                    return Response(
                        {"detail": "Failed to create payment request."},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

                payment.provider_data = provider_response
                payment.save(update_fields=["provider_data", "updated_at"])

        response_data = {
            "payment_id": payment.id,
            "status": payment.status,
        }

        if payment_method == Payment.Method.WALLET:
            response_data["simulate_payment_url"] = f"/api/payments/verify/?payment_id={payment.id}"

        if provider_response:
            response_data["payment_url"] = provider_response.get("link")

        return Response(response_data, status=status.HTTP_201_CREATED)


class VerifyPaymentView(generics.GenericAPIView):
    """Callback endpoint for IDPay payments."""

    permission_classes = [IsAuthenticated]

    REQUIRED_FIELDS = ("id", "order_id", "status")

    def post(self, request, *args, **kwargs):
        data = request.data or {}

        missing_fields = [field for field in self.REQUIRED_FIELDS if field not in data]
        if missing_fields:
            return Response(
                {
                    "detail": "Missing required fields.",
                    "missing_fields": missing_fields,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider_payment_id = data.get("id")
        order_id = data.get("order_id")
        status_code = data.get("status")

        try:
            status_code = int(status_code)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid status value."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order_id_int = int(order_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid order_id value."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                payment = (
                    Payment.objects.select_for_update()
                    .select_related("appointment")
                    .get(id=order_id_int)
                )
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found."}, status=404)

            if payment.user_id != request.user.id:
                return Response(
                    {"detail": "You are not allowed to verify this payment."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if str(order_id) != str(payment.id):
                return Response(
                    {"detail": "order_id does not match payment."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if status_code in (100, 101):
                try:
                    provider_response = payment_utils.verify_payment_request(
                        provider_payment_id
                    )
                except Exception:
                    payment.mark_failed()
                    return Response(
                        {"detail": "Payment verification failed."},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

                payment.transaction_id = provider_payment_id
                payment.provider_data = provider_response
                payment.save(update_fields=["transaction_id", "provider_data", "updated_at"])
                payment.mark_completed()

                return Response(
                    {
                        "status": "Payment confirmed ✅",
                        "appointment_status": payment.appointment.status
                        if payment.appointment
                        else None,
                        "meet_link": getattr(
                            payment.appointment, "google_meet_link", None
                        ),
                        "provider_status": provider_response.get("status"),
                    },
                    status=status.HTTP_200_OK,
                )

            payment.mark_failed()
            return Response(
                {"detail": "Payment status is not successful.", "status_code": status_code},
                status=status.HTTP_400_BAD_REQUEST,
            )


class WalletDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WalletSerializer

    def get_object(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


class WalletTopUpView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WalletTopUpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wallet = serializer.save()
        return Response(WalletSerializer(wallet).data, status=status.HTTP_200_OK)


class WalletReserveView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WalletReserveSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment, wallet = serializer.save()
        data = WalletSerializer(wallet).data
        data.update({
            "payment_id": payment.id,
            "reserved_amount": str(payment.wallet_reserved_amount),
        })
        return Response(data, status=status.HTTP_200_OK)