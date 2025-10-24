from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import OnlineSlot, OnlineAppointment
from .serializers import OnlineSlotSerializer, OnlineAppointmentSerializer, OnlineAppointmentCancelSerializer, OnlineAppointmentRescheduleSerializer
from django.utils import timezone
from rest_framework import serializers
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from notifications.models import Notification
from common.utils import send_sms

from .integrations import CalendarService, CalendarSyncError


# لیست اسلات‌های آنلاین برای یک وکیل
class OnlineSlotListView(generics.ListAPIView):
    serializer_class = OnlineSlotSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        lawyer_id = self.kwargs['lawyer_id']
        return OnlineSlot.objects.filter(lawyer_id=lawyer_id, is_booked=False, start_time__gte=timezone.now())

# رزرو آنلاین یک اسلات
class OnlineAppointmentCreateView(generics.CreateAPIView):
    serializer_class = OnlineAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        self.calendar_sync_result = None
        response = super().create(request, *args, **kwargs)
        result = getattr(self, "calendar_sync_result", None)
        if result and not result.success and result.message:
            data = dict(response.data)
            data['calendar_sync_warning'] = result.message
            response.data = data
        return response

    def perform_create(self, serializer):
        slot_id = self.request.data.get('slot')
        slot = get_object_or_404(OnlineSlot, pk=slot_id)

        client_profile = getattr(self.request.user, 'client_profile', None)
        if not client_profile:
            raise serializers.ValidationError("فقط کلاینت‌ها می‌توانند رزرو کنند.")

        appointment = serializer.save(client=client_profile, lawyer=slot.lawyer, slot=slot)
        calendar_service = CalendarService()
        self.calendar_sync_result = appointment.confirm(calendar_service=calendar_service)

# لیست رزروهای آنلاین کاربر
class OnlineAppointmentListView(generics.ListAPIView):
    serializer_class = OnlineAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        client_profile = getattr(self.request.user, 'client_profile', None)
        return OnlineAppointment.objects.filter(client=client_profile).order_by('-slot__start_time')
    
class CancelOnlineAppointmentAPIView(APIView):
    """
    POST /api/online/appointments/{pk}/cancel/
    فقط کاربر (client) می‌تواند تا 24 ساعت قبل لغو کند.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        appointment = get_object_or_404(OnlineAppointment.objects.select_related("client__user", "slot"), pk=pk)

        if appointment.client.user != user:
            return Response({"detail": "فقط کاربر صاحب رزرو می‌تواند آن را لغو کند."}, status=status.HTTP_403_FORBIDDEN)

        if appointment.status in ["cancelled", "completed"]:
            return Response({"detail": "این رزرو قابل لغو نیست."}, status=status.HTTP_400_BAD_REQUEST)

        if appointment.slot.start_time - timezone.now() < timedelta(hours=24):
            return Response({"detail": "لغو تنها تا 24 ساعت قبل امکان‌پذیر است."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OnlineAppointmentCancelSerializer(data=request.data or {"confirm": True})
        serializer.is_valid(raise_exception=True)

        try:
            result = appointment.cancel(user=user, calendar_service=CalendarService())
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "خطا در لغو رزرو."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        appointment.refresh_from_db(fields=["status", "calendar_event_id"])

        try:
            Notification.objects.create(
                user=user,
                appointment=appointment,
                title="رزرو لغو شد",
                message=f"رزروی که برای {appointment.slot.start_time} با {appointment.lawyer.user.get_full_name()} داشتید، لغو شد.",
            )
            Notification.objects.create(
                user=appointment.lawyer.user,
                appointment=appointment,
                title="رزرو کاربر لغو شد",
                message=f"{user.get_full_name()} رزوی که داشت را برای {appointment.slot.start_time} لغو کرد.",
            )
        except Exception:
            pass

        try:
            send_sms(user.phone_number, f"رزرو شما برای {appointment.slot.start_time} لغو شد.")
            send_sms(appointment.lawyer.user.phone_number, f"رزرو کاربر {user.get_full_name()} برای {appointment.slot.start_time} لغو شد.")
        except Exception:
            pass

        response_data = {"detail": "رزرو با موفقیت لغو شد."}
        if result and not result.success and result.message:
            response_data["calendar_sync_warning"] = result.message

        return Response(response_data, status=status.HTTP_200_OK)

class RescheduleOnlineAppointmentAPIView(APIView):
    """
    POST /api/online/appointments/{pk}/reschedule/
    فقط کاربر می‌تواند تا 24 ساعت قبل درخواست تغییر زمان بدهد.
    شرایط:
      - اسلات جدید باید آزاد باشد
      - کاربر نباید بیش از 1 رزرو در آن روز داشته باشد (بر اساس اسلات جدید)
      - همه عملیات در یک تراکنش انجام می‌شود (race-safe)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        appointment = get_object_or_404(OnlineAppointment.objects.select_related("client__user", "slot", "lawyer"), pk=pk)

        # فقط صاحب رزرو
        if appointment.client.user != user:
            return Response({"detail": "فقط کاربر صاحب رزرو می‌تواند زمان را تغییر دهد."}, status=status.HTTP_403_FORBIDDEN)

        if appointment.status in ["cancelled", "completed"]:
            return Response({"detail": "این رزرو قابل تغییر نیست."}, status=status.HTTP_400_BAD_REQUEST)

        # حداکثر تا 24 ساعت قبل
        if appointment.slot.start_time - timezone.now() < timedelta(hours=24):
            return Response({"detail": "تغییر زمان تنها تا 24 ساعت قبل امکان‌پذیر است."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OnlineAppointmentRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_slot_id = serializer.validated_data["new_slot_id"]

        # بررسی وجود اسلات جدید
        new_slot = get_object_or_404(OnlineSlot, pk=new_slot_id)

        # prevent reschedule to same slot
        if new_slot.pk == appointment.slot.pk:
            return Response({"detail": "انتخاب اسلات جدید نمی‌تواند همان اسلات فعلی باشد."}, status=status.HTTP_400_BAD_REQUEST)

        # بررسی اینکه اسلات جدید مربوط به همان وکیل باشه (در صورت نیاز)
        if new_slot.lawyer != appointment.lawyer:
            return Response({"detail": "اسلات جدید باید متعلق به همان وکیل باشد."}, status=status.HTTP_400_BAD_REQUEST)

        # بررسی محدودیت 1 رزرو در روز برای کاربر (بر اساس تاریخ اسلات جدید)
        new_date = new_slot.start_time.date()
        if OnlineAppointment.objects.filter(
            client=appointment.client,
            slot__start_time__date=new_date,
            status="confirmed"
        ).exclude(pk=appointment.pk).exists():
            return Response({"detail": "شما قبلاً یک رزرو تأیید شده در آن روز دارید."}, status=status.HTTP_400_BAD_REQUEST)

        calendar_sync_warning = None
        try:
            with transaction.atomic():
                # قفل روی appointment، old slot و new slot
                appt = OnlineAppointment.objects.select_for_update().get(pk=appointment.pk)
                old_slot = OnlineSlot.objects.select_for_update().get(pk=appt.slot.pk)
                ns = OnlineSlot.objects.select_for_update().get(pk=new_slot.pk)

                # بررسی مجدد داخل تراکنش
                if appt.status in ["cancelled", "completed"]:
                    return Response({"detail": "این رزرو قابل تغییر نیست."}, status=status.HTTP_400_BAD_REQUEST)
                if old_slot.start_time - timezone.now() < timedelta(hours=24):
                    return Response({"detail": "تغییر زمان تنها تا 24 ساعت قبل امکان‌پذیر است."}, status=status.HTTP_400_BAD_REQUEST)
                if ns.is_booked:
                    return Response({"detail": "اسلات جدید قبلاً رزرو شده است."}, status=status.HTTP_400_BAD_REQUEST)

                # آزادسازی اسلات قدیمی
                old_slot.is_booked = False
                old_slot.save(update_fields=["is_booked"])

                # رزرو اسلات جدید
                ns.is_booked = True
                ns.save(update_fields=["is_booked"])

                # بروزرسانی appointment
                appt.slot = ns
                appt.status = "confirmed"
                # اگر لازم باشه، لینک جدید Google Meet ساخته و جایگزین شود
                # appt.google_meet_link = appt.create_google_meet_link()
                appt.save(update_fields=["slot", "status", "google_meet_link"])

            calendar_service = CalendarService()
            try:
                calendar_service.update_event(appt)
            except CalendarSyncError as exc:
                calendar_sync_warning = str(exc)

            # خارج از تراکنش: ارسال نوتیف و sms
            try:
                Notification.objects.create(
                    user=user,
                    appointment=appt,
                    title="رزرو تغییر کرد",
                    message=f"رزرو شما به زمان {ns.start_time} منتقل شد."
                )
                Notification.objects.create(
                    user=appt.lawyer.user,
                    appointment=appt,
                    title="رزرو کاربر تغییر یافت",
                    message=f"رزرو {user.get_full_name()} به زمان {ns.start_time} تغییر یافت."
                )
            except Exception:
                pass

            try:
                send_sms(user.phone_number, f"رزرو شما به زمان {ns.start_time} تغییر یافت.")
                send_sms(appt.lawyer.user.phone_number, f"رزرو کاربر {user.get_full_name()} به زمان {ns.start_time} تغییر یافت.")
            except Exception:
                pass

            response_data = {"detail": "رزرو با موفقیت تغییر یافت.", "appointment_id": appt.pk}
            if calendar_sync_warning:
                response_data["calendar_sync_warning"] = calendar_sync_warning
            return Response(response_data, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": "خطا در تغییر زمان رزرو."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
