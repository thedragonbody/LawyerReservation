from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import Payment, Wallet
from appointments.models import InPersonAppointment, OnlineAppointment
from ai_assistant.models import Subscription
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
        subscription_id = request.data.get("subscription_id")
        inperson_appointment_id = request.data.get("inperson_appointment_id") or request.data.get(
            "inperson_appointment"
        )
        amount = request.data.get("amount")

        related_params = [value for value in [appointment_id, subscription_id, inperson_appointment_id] if value]
        if not related_params:
            return Response(
                {"error": "Missing appointment_id, subscription_id, or inperson_appointment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(related_params) > 1:
            return Response(
                {"detail": "Only one of appointment_id, subscription_id, or inperson_appointment can be provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not amount:
            return Response({"error": "Missing amount"}, status=status.HTTP_400_BAD_REQUEST)

        appointment = None
        subscription = None
        inperson_appointment = None

        if appointment_id:
            try:
                appointment = OnlineAppointment.objects.get(
                    id=appointment_id, client__user=request.user
                )
            except OnlineAppointment.DoesNotExist:
                return Response({"error": "Appointment not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)
        elif subscription_id:
            try:
                subscription = Subscription.objects.get(id=subscription_id, user=request.user)
            except Subscription.DoesNotExist:
                return Response({"error": "Subscription not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)
        elif inperson_appointment_id:
            try:
                inperson_appointment = InPersonAppointment.objects.get(
                    id=inperson_appointment_id, client__user=request.user
                )
            except InPersonAppointment.DoesNotExist:
                return Response(
                    {"error": "In-person appointment not found or unauthorized"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        related_filter = {}
        duplicate_error = "Payment already completed for this appointment."
        if appointment:
            related_filter = {"appointment": appointment}
        elif subscription:
            related_filter = {"subscription": subscription}
            duplicate_error = "Payment already completed for this subscription."
        elif inperson_appointment:
            related_filter = {"inperson_appointment": inperson_appointment}
            duplicate_error = "Payment already completed for this in-person appointment."

        if related_filter and Payment.objects.filter(status=Payment.Status.COMPLETED, **related_filter).exists():
            return Response({"detail": duplicate_error}, status=status.HTTP_400_BAD_REQUEST)

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
                subscription=subscription,
                inperson_appointment=inperson_appointment,
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


class IDPayCallbackView(APIView):
    """Handle IDPay webhook callbacks without requiring authentication."""

    permission_classes = [AllowAny]

    SUCCESS_STATUSES = {100, 101}

    def post(self, request, *args, **kwargs):
        order_id = request.data.get("order_id")
        status_value = request.data.get("status")
        track_id = request.data.get("track_id")

        if not order_id:
            return Response({"detail": "order_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order_id_int = int(order_id)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid order_id."}, status=status.HTTP_400_BAD_REQUEST)

        if track_id in (None, ""):
            return Response({"detail": "track_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            status_int = int(status_value)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid status value."}, status=status.HTTP_400_BAD_REQUEST)

        provider_payload = {key: request.data.get(key) for key in request.data}

        with transaction.atomic():
            try:
                payment = Payment.objects.select_for_update().get(id=order_id_int)
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

            update_fields = []
            if payment.transaction_id != track_id:
                payment.transaction_id = track_id
                update_fields.append("transaction_id")

            if status_int in self.SUCCESS_STATUSES:
                if update_fields:
                    update_fields.append("updated_at")
                    payment.save(update_fields=update_fields)
                payment.mark_completed(provider_data=provider_payload)
                result_status = payment.status
                message = "Payment completed."
            else:
                update_fields.append("provider_data")
                payment.provider_data = provider_payload
                update_fields.append("updated_at")
                payment.save(update_fields=update_fields)
                payment.mark_failed()
                payment.refresh_from_db(fields=["status"])
                result_status = payment.status
                message = "Payment failed."

        return Response({"detail": message, "status": result_status}, status=status.HTTP_200_OK)


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