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
from ai_assistant.serializers import SubscriptionCreateSerializer

from .models import Payment
from .serializers import PaymentSerializer
from appointments.models import Appointment
from .utils import create_payment_request, verify_payment_request
from common.utils import send_user_notification, send_sms

# subscription models (optional)
try:
    from ai_assistant.models import Subscription, AIPlan
except Exception:
    Subscription = None
    AIPlan = None

logger = logging.getLogger("payments")


# ==============================
# Payment Create (appointment)
# ==============================
class PaymentCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, id=appointment_id, client__user=request.user)

        if appointment.status == Appointment.Status.CONFIRMED:
            return Response({"detail": "Appointment already confirmed."}, status=400)

        amount_decimal = getattr(appointment.slot, "price", Decimal("500000"))
        multiplier = getattr(__import__("django.conf").conf.settings, "PAYMENT_AMOUNT_MULTIPLIER", 1)
        amount_int = int(amount_decimal * Decimal(multiplier))

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

        if str(provider_status) == "100":
            with transaction.atomic():
                appointment = payment.appointment
                slot = appointment.slot

                if appointment.status != Appointment.Status.CONFIRMED:
                    if not getattr(slot, "is_booked", False):
                        slot.is_booked = True
                        slot.save(update_fields=["is_booked"])

                    appointment.status = Appointment.Status.CONFIRMED
                    if hasattr(appointment, "transaction_id"):
                        appointment.transaction_id = payment.transaction_id
                        appointment.save(update_fields=["status", "transaction_id"])
                    else:
                        appointment.save(update_fields=["status"])

                if hasattr(payment, "mark_completed") and callable(getattr(payment, "mark_completed")):
                    payment.mark_completed(provider_data=provider_res)
                else:
                    payment.status = Payment.Status.COMPLETED
                    payment.save(update_fields=["status", "provider_data"])

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

        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "provider_data"])
        return Response({"detail": "Payment failed"}, status=400)


# ==============================
# Payment List
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
# Payment Cancel / Refund
# ==============================
class PaymentCancelView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):
        payment = Payment.objects.filter(id=payment_id, user=request.user).first()
        if not payment:
            return Response({"detail": "Payment not found."}, status=404)

        if payment.status != Payment.Status.COMPLETED:
            return Response({"detail": "Only completed payments can be cancelled."}, status=400)

        if timezone.now() - payment.created_at > timedelta(hours=24):
            return Response({"detail": "Cancellation period expired (24h limit)."}, status=403)

        appointment = payment.appointment
        slot = appointment.slot

        with transaction.atomic():
            appointment.status = Appointment.Status.CANCELLED
            appointment.save(update_fields=["status"])
            if getattr(slot, "is_booked", False):
                slot.is_booked = False
                slot.save(update_fields=["is_booked"])

            if hasattr(payment, "mark_refunded") and callable(getattr(payment, "mark_refunded")):
                payment.mark_refunded()
            else:
                if hasattr(Payment.Status, "REFUNDED"):
                    payment.status = Payment.Status.REFUNDED
                else:
                    payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status"])

        try:
            send_user_notification(
                request.user,
                "رزرو لغو شد و وجه بازگشت داده شد",
                f"رزرو شما لغو شد."
            )
        except Exception as e:
            logger.warning("send_user_notification failed: %s", e)

        try:
            send_sms(
                request.user.phone_number,
                f"رزرو شما لغو شد و وجه بازگشت داده شد."
            )
        except Exception as e:
            logger.warning("send_sms failed: %s", e)

        return Response({"detail": "Payment cancelled and appointment slot released."}, status=200)


# ==============================
# Subscription Payment Create
# ==============================
class CreateSubscriptionPaymentView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionCreateSerializer  # <<< مهم: رفع خطای AssertionError

    def get(self, request, *args, **kwargs):
        """
        برگرداندن لیست پلن‌ها (Front-end برای نمایش انتخاب پلن استفاده می‌کند).
        """
        plans = AIPlan.objects.all().order_by("daily_limit")
        data = [{"id": p.id, "name": p.name, "daily_limit": p.daily_limit, "monthly_limit": p.monthly_limit, "price_cents": p.price_cents} for p in plans]
        return Response({"plans": data}, status=200)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan_id = serializer.validated_data["plan_id"]
        payment_method = serializer.validated_data.get("payment_method", "idpay")

        try:
            plan = AIPlan.objects.get(id=plan_id)
        except AIPlan.DoesNotExist:
            return Response({"detail": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)

        # create pending sub & payment (exact logic شبیه کدی که قبلاً گذاشتی)
        sub = Subscription.objects.create(
            user=request.user,
            plan=plan,
            active=False,
            starts_at=timezone.now(),
        )

        payment_kwargs = {
            "user": request.user,
            "amount": Decimal(plan.price_cents) / Decimal(100) if getattr(plan, "price_cents", None) is not None else Decimal("0"),
            "payment_method": payment_method,
            "status": Payment.Status.PENDING
        }
        if "subscription" in [f.name for f in Payment._meta.get_fields()]:
            payment_kwargs["subscription_id"] = sub.id

        payment = Payment.objects.create(**payment_kwargs)
        # callback واقعی برای درگاه:
        callback_url = request.build_absolute_uri("/api/payments/subscription/payment-callback/")
        # اگر میخوای لینک واقعی بگیری از create_payment_request استفاده کن، الان برای تست لینک محلی:
        payment_link = f"https://payment.gateway/pay/{payment.id}"

        return Response({
            "payment_id": payment.id,
            "payment_link": payment_link,
            "subscription_id": sub.id
        }, status=status.HTTP_201_CREATED)

# ==============================
# Subscription Payment Callback
# ==============================
class PaymentCallbackView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payment_id = request.data.get("payment_id") or request.data.get("id")
        status_received = request.data.get("status")

        if not payment_id:
            return Response({"detail": "payment_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        if status_received == "completed":
            if hasattr(payment, "mark_completed") and callable(getattr(payment, "mark_completed")):
                payment.mark_completed(provider_data=request.data)
            else:
                payment.status = Payment.Status.COMPLETED
                payment.provider_data = request.data
                payment.save(update_fields=["status", "provider_data"])

            sub = None
            if Subscription is not None:
                if hasattr(payment, "subscription"):
                    sub = getattr(payment, "subscription")
                else:
                    sub_id = request.data.get("subscription_id") or (payment.provider_data or {}).get("subscription_id")
                    if sub_id:
                        sub = Subscription.objects.filter(id=sub_id).first()

            if sub:
                sub.active = True
                plan = getattr(sub, "plan", None)
                if plan:
                    duration = getattr(plan, "duration", None) or getattr(plan, "duration_days", None)
                    if isinstance(duration, int):
                        sub.ends_at = timezone.now() + timedelta(days=int(duration))
                sub.save()

        elif status_received == "failed":
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])

        return Response({"status": payment.status}, status=200)