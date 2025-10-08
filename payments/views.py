from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

from .models import Payment
from .serializers import PaymentSerializer
from appointments.models import Appointment
from .utils import create_payment_request, verify_payment_request
from common.utils import send_user_notification, send_sms

logger = logging.getLogger("payments")


# ==============================
# Payment Create
# ==============================
class PaymentCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, appointment_id):
        """ایجاد تراکنش جدید برای رزرو یک نوبت"""
        appointment = get_object_or_404(Appointment, id=appointment_id, client__user=request.user)

        if appointment.status == Appointment.Status.CONFIRMED:
            return Response({"detail": "Appointment already confirmed."}, status=400)

        # مبلغ از slot گرفته می‌شود
        amount_decimal = getattr(appointment.slot, "price", Decimal("500000"))
        multiplier = getattr(__import__("django.conf").conf.settings, "PAYMENT_AMOUNT_MULTIPLIER", 1)
        amount_int = int(amount_decimal * Decimal(multiplier))

        # ساخت پرداخت اولیه
        payment = Payment.objects.create(
            appointment=appointment,
            user=request.user,
            amount=amount_decimal,
            status=Payment.Status.PENDING
        )

        callback_url = request.build_absolute_uri("/api/payments/verify/")

        try:
            provider_resp = create_payment_request(
                order_id=payment.id,
                amount=amount_int,
                callback=callback_url,
                phone=getattr(request.user, "phone_number", "")
            )
        except Exception as e:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            logger.exception("Payment creation failed: %s", e)
            return Response({"detail": "Payment gateway error"}, status=500)

        tx_id = provider_resp.get("id") or provider_resp.get("track_id") or provider_resp.get("trans_id")
        payment.transaction_id = str(tx_id) if tx_id else None
        payment.provider_data = provider_resp
        payment.save(update_fields=["transaction_id", "provider_data"])

        return Response({
            "payment_link": provider_resp.get("link"),
            "payment_id": payment.transaction_id,
            "order_id": payment.id
        }, status=200)


# ==============================
# Payment Verify
# ==============================
class PaymentVerifyView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """تایید وضعیت پرداخت از سمت درگاه"""
        data = request.data
        payment_id = data.get("id") or data.get("payment_id") or data.get("transaction_id")
        order_id = data.get("order_id") or data.get("orderId")

        payment = None
        if order_id:
            payment = Payment.objects.filter(id=order_id).first()
        if not payment and payment_id:
            payment = Payment.objects.filter(transaction_id=str(payment_id)).first()

        if not payment:
            logger.warning("Payment not found for verify payload: %s", data)
            return Response({"detail": "Payment not found"}, status=404)

        if payment.status == Payment.Status.COMPLETED:
            return Response({"detail": "Payment already completed."}, status=200)

        try:
            provider_res = verify_payment_request(payment.transaction_id)
        except Exception as e:
            logger.exception("Provider verify failed: %s", e)
            return Response({"detail": "Provider verify failed"}, status=502)

        payment.provider_data = provider_res
        provider_status = provider_res.get("status") or provider_res.get("result", {}).get("status")

        # ✅ پرداخت موفق
        if str(provider_status) == "100":
            with transaction.atomic():
                appointment = payment.appointment
                slot = appointment.slot

                # جلوگیری از اجرای تکراری (idempotent)
                if appointment.status == Appointment.Status.CONFIRMED:
                    return Response({"detail": "Appointment already confirmed."}, status=200)

                # بروز رسانی slot و appointment
                if not slot.is_booked:
                    slot.is_booked = True
                    slot.save(update_fields=["is_booked"])

                appointment.status = Appointment.Status.CONFIRMED
                appointment.transaction_id = payment.transaction_id
                appointment.save(update_fields=["status", "transaction_id"])

                payment.status = Payment.Status.COMPLETED
                payment.save(update_fields=["status", "provider_data"])

            # ارسال نوتیف و پیامک
            try:
                send_user_notification(
                    appointment.client.user,
                    "پرداخت موفق و وقت تایید شد",
                    f"وقت شما با {appointment.lawyer.user.get_full_name()} در {slot.start_time} تایید شد."
                )
            except Exception as e:
                logger.warning("send_user_notification failed: %s", e)

            try:
                send_sms(
                    appointment.client.user.phone_number,
                    f"پرداخت موفق! وقت شما {slot.start_time} با {appointment.lawyer.user.get_full_name()} تایید شد."
                )
            except Exception as e:
                logger.warning("send_sms failed: %s", e)

            return Response({"detail": "Payment verified and appointment confirmed."}, status=200)

        # ❌ پرداخت ناموفق
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "provider_data"])
        return Response({"detail": "Payment failed"}, status=400)


# ==============================
# Payment List (Paginated)
# ==============================
class PaymentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaymentPagination

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by('-created_at')


# ==============================
# Cancel Payment / Refund
# ==============================
class PaymentCancelView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):
        """لغو رزرو و بازگشت پول ظرف ۲۴ ساعت"""
        payment = Payment.objects.filter(id=payment_id, user=request.user).first()
        if not payment:
            return Response({"detail": "Payment not found."}, status=404)

        if payment.status != Payment.Status.COMPLETED:
            return Response({"detail": "Only completed payments can be cancelled."}, status=400)

        # بررسی محدودیت ۲۴ ساعته
        if timezone.now() - payment.created_at > timedelta(hours=24):
            return Response({"detail": "Cancellation period expired (24h limit)."}, status=403)

        appointment = payment.appointment
        slot = appointment.slot

        with transaction.atomic():
            # لغو رزرو
            appointment.status = Appointment.Status.CANCELLED
            appointment.save(update_fields=["status"])

            # آزادسازی Slot
            slot.is_booked = False
            slot.save(update_fields=["is_booked"])

            # بروزرسانی پرداخت
            payment.status = Payment.Status.REFUNDED
            payment.save(update_fields=["status"])

        # اطلاع‌رسانی
        try:
            send_user_notification(
                request.user,
                "رزرو لغو شد و وجه بازگشت داده شد",
                f"رزرو شما با {appointment.lawyer.user.get_full_name()} در {slot.start_time} لغو شد."
            )
        except Exception as e:
            logger.warning("send_user_notification failed: %s", e)

        try:
            send_sms(
                request.user.phone_number,
                f"رزرو شما لغو شد و وجه بازگشت داده شد. وقت {slot.start_time} با {appointment.lawyer.user.get_full_name()} لغو شد."
            )
        except Exception as e:
            logger.warning("send_sms failed: %s", e)

        return Response({"detail": "Payment cancelled and appointment slot released."}, status=200)