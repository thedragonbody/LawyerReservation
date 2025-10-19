from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from payments.models import Payment
from appointments.models import OnlineAppointment
from payments.serializers import PaymentSerializer


class CreatePaymentView(generics.CreateAPIView):
    """
    کاربر رزرو آنلاین انجام داده → درخواست پرداخت ایجاد می‌کند.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def post(self, request, *args, **kwargs):
        appointment_id = request.data.get("online_appointment_id")
        amount = request.data.get("amount")

        if not appointment_id or not amount:
            return Response({"error": "Missing online_appointment_id or amount"}, status=400)

        try:
            appointment = OnlineAppointment.objects.get(
                id=appointment_id, client__user=request.user
            )
        except OnlineAppointment.DoesNotExist:
            return Response({"error": "Appointment not found or unauthorized"}, status=404)

        # جلوگیری از ایجاد پرداخت تکراری
        if hasattr(appointment, "payment") and appointment.payment.status == Payment.Status.COMPLETED:
            return Response({"detail": "Payment already completed for this appointment."}, status=400)

        with transaction.atomic():
            payment = Payment.objects.create(
                user=request.user,
                online_appointment=appointment,
                amount=amount,
                payment_method="simulation",
            )

        return Response({
            "payment_id": payment.id,
            "status": payment.status,
            "simulate_payment_url": f"/api/payments/verify/?payment_id={payment.id}",
        }, status=status.HTTP_201_CREATED)


class VerifyPaymentView(generics.GenericAPIView):
    """
    ✅ شبیه‌سازی پرداخت موفق (در آینده درگاه واقعی جایگزین می‌شود)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        payment_id = request.query_params.get("payment_id")

        try:
            payment = Payment.objects.select_for_update().get(
                id=payment_id, user=request.user
            )
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        with transaction.atomic():
            payment.mark_completed(provider_data={"simulated": True})

        return Response({
            "status": "Payment confirmed ✅",
            "appointment_status": payment.online_appointment.status,
            "meet_link": payment.online_appointment.meet_link,
        }, status=status.HTTP_200_OK)