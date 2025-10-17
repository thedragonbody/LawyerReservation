from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from rest_framework.exceptions import ValidationError
from notifications.models import Notification
from rest_framework.views import APIView

from common.models import LawyerClientRelation
from .models import Slot, Appointment
from .serializers import AppointmentSerializer
from common.choices import AppointmentStatus
from payments.models import Payment
from payments.utils import create_payment_request, verify_payment_request
from common.utils import send_sms, send_user_notification


class AppointmentCreateView(generics.GenericAPIView):
    """
    ایجاد درخواست پرداخت و رزرو بعد از پرداخت موفق.
    """
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client = request.user.client_profile
        slot = serializer.validated_data['slot']

        # Validation: end_time > start_time
        if slot.end_time <= slot.start_time:
            raise ValidationError({"slot": "Slot end_time must be after start_time."})

        # بررسی همزمانی slot
        with transaction.atomic():
            slot = Slot.objects.select_for_update().get(pk=slot.id)
            if slot.is_booked:
                raise ValidationError({"slot": "This slot is already booked."})

        # ایجاد درخواست پرداخت
        callback_url = request.build_absolute_uri("/appointments/payment-callback/")
        try:
            payment_resp = create_payment_request(
                order_id=f"appointment_{slot.id}_{client.user.id}",
                amount=int(slot.price),
                callback=callback_url,
                phone=client.user.phone_number,
                mail=client.user.email,
                desc=f"Payment for appointment with {slot.lawyer.user.get_full_name()}"
            )
        except Exception as e:
            return Response({"detail": "Payment request failed.", "error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ثبت Payment با وضعیت Pending
        Payment.objects.create(
            user=client.user,
            appointment=None,
            amount=slot.price,
            status=Payment.Status.PENDING,
            payment_method="idpay",
            transaction_id=payment_resp.get("id"),
            provider_data=payment_resp
        )

        return Response({
            "payment_url": payment_resp.get("link"),
            "detail": "Proceed to payment to confirm your appointment."
        }, status=status.HTTP_200_OK)


class AppointmentPaymentCallbackView(APIView):
    """
    Callback برای تایید پرداخت و ایجاد رزرو نهایی.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        transaction_id = request.data.get("transaction_id")
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        if payment.user != request.user:
            return Response({"detail": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        # Verify payment
        try:
            payment_response = verify_payment_request(transaction_id)
        except Exception:
            return Response({"detail": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)

        if payment_response.get("status") != 100:
            payment.status = Payment.Status.FAILED
            payment.save()
            return Response({"detail": "Payment failed."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            slot_id = int(payment_response["order_id"].split("_")[1])
            slot = Slot.objects.select_for_update().get(pk=slot_id)
            if slot.is_booked:
                return Response({"detail": "Slot already booked."}, status=status.HTTP_400_BAD_REQUEST)

            appointment = Appointment.objects.create(
                client=payment.user.client_profile,
                lawyer=slot.lawyer,
                slot=slot,
                status=AppointmentStatus.CONFIRMED,
                transaction_id=transaction_id
            )

            slot.is_booked = True
            slot.save()

            # تکمیل Payment
            payment.appointment = appointment
            payment.status = Payment.Status.COMPLETED
            payment.provider_data = payment_response
            payment.save()

            # به‌روزرسانی رابطه Lawyer ↔ Client
            relation, _ = LawyerClientRelation.objects.get_or_create(
                lawyer=slot.lawyer,
                client=payment.user.client_profile,
            )
            relation.is_active = True
            relation.touch()  # آپدیت last_interaction
            relation.save()

        # Notification و پیامک
        send_user_notification(
            user=appointment.client.user,
            title="Appointment Confirmed",
            message=f"Your appointment on {slot.start_time} with {slot.lawyer.user.get_full_name()} has been confirmed.",
            link=None
        )

        send_sms(
            appointment.client.user.phone_number,
            f"پرداخت موفق! وقت شما {slot.start_time} با {slot.lawyer.user.get_full_name()} تایید شد."
        )

        return Response({"detail": "Appointment confirmed successfully."}, status=status.HTTP_200_OK)