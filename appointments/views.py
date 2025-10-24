from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.choices import AppointmentStatus
from common.utils import send_sms
from notifications.models import Notification

from .integrations import CalendarService, CalendarSyncError
from .models import OnsiteAppointment, OnsiteSlot, OnlineAppointment, OnlineSlot
from .serializers import (
    OnlineAppointmentCancelSerializer,
    OnlineAppointmentRescheduleSerializer,
    OnlineAppointmentSerializer,
    OnlineSlotSerializer,
    OnsiteAppointmentSerializer,
    OnsiteSlotSerializer,
)



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
        self.created_appointment = None
        response = super().create(request, *args, **kwargs)
        data = dict(response.data)

        appointment = getattr(self, "created_appointment", None)
        if appointment:
            office_info = appointment.lawyer.get_office_location()
            if office_info:
                meaningful_office_values = [
                    office_info.get("address"),
                    office_info.get("latitude"),
                    office_info.get("longitude"),
                    office_info.get("map_url"),
                    office_info.get("map_embed_url"),
                ]
                if any(value not in (None, "") for value in meaningful_office_values):
                    data["office"] = office_info

        result = getattr(self, "calendar_sync_result", None)
        if result and not result.success and result.message:
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
        self.created_appointment = appointment
        calendar_service = CalendarService()
        self.calendar_sync_result = appointment.confirm(calendar_service=calendar_service)

# لیست رزروهای آنلاین کاربر
class OnlineAppointmentListView(generics.ListAPIView):
    serializer_class = OnlineAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        client_profile = getattr(self.request.user, 'client_profile', None)
        return (
            OnlineAppointment.objects.select_related('slot', 'lawyer__user')
            OnlineAppointment.objects.select_related("slot", "lawyer__user")
            .filter(client=client_profile)
            .order_by('-slot__start_time')
        )
    
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
            result = appointment.cancel(
                user=user,
                calendar_service=CalendarService(),
                send_notifications=True,
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "خطا در لغو رزرو."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        appointment.refresh_from_db(fields=["status", "calendar_event_id"])

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


class OnsiteSlotListCreateView(generics.ListCreateAPIView):
    serializer_class = OnsiteSlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lawyer_profile = getattr(self.request.user, "lawyer_profile", None)
        if not lawyer_profile:
            return OnsiteSlot.objects.none()
        return OnsiteSlot.objects.filter(lawyer=lawyer_profile).order_by("start_time")

    def perform_create(self, serializer):
        lawyer_profile = getattr(self.request.user, "lawyer_profile", None)
        if not lawyer_profile:
            raise serializers.ValidationError("فقط وکلا می‌توانند اسلات حضوری ثبت کنند.")
        serializer.save(lawyer=lawyer_profile)


class OnsiteSlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OnsiteSlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lawyer_profile = getattr(self.request.user, "lawyer_profile", None)
        if not lawyer_profile:
            return OnsiteSlot.objects.none()
        return OnsiteSlot.objects.filter(lawyer=lawyer_profile)

    def perform_destroy(self, instance):
        if instance.appointments.exclude(status=AppointmentStatus.CANCELLED).exists():
            raise serializers.ValidationError("امکان حذف اسلات رزرو شده وجود ندارد.")
        instance.delete()


class OnsiteAppointmentListCreateView(generics.ListCreateAPIView):
    serializer_class = OnsiteAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lawyer_profile = getattr(self.request.user, "lawyer_profile", None)
        client_profile = getattr(self.request.user, "client_profile", None)

        if lawyer_profile:
            return OnsiteAppointment.objects.filter(lawyer=lawyer_profile).order_by("-slot__start_time")
        if client_profile:
            return OnsiteAppointment.objects.filter(client=client_profile).order_by("-slot__start_time")
        return OnsiteAppointment.objects.none()

    def perform_create(self, serializer):
        client_profile = getattr(self.request.user, "client_profile", None)
        if not client_profile:
            raise serializers.ValidationError("فقط موکلین می‌توانند رزرو حضوری ثبت کنند.")
        slot = serializer.validated_data.get("slot")
        if slot is None:
            raise serializers.ValidationError({"slot": "انتخاب اسلات الزامی است."})
        serializer.save(client=client_profile, lawyer=slot.lawyer)


class OnsiteAppointmentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OnsiteAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lawyer_profile = getattr(self.request.user, "lawyer_profile", None)
        client_profile = getattr(self.request.user, "client_profile", None)

        if lawyer_profile:
            return OnsiteAppointment.objects.filter(lawyer=lawyer_profile)
        if client_profile:
            return OnsiteAppointment.objects.filter(client=client_profile)
        return OnsiteAppointment.objects.none()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        status_value = request.data.get("status")

        if status_value is None:
            return Response({"detail": "فقط بروزرسانی وضعیت پشتیبانی می‌شود."}, status=status.HTTP_400_BAD_REQUEST)

        if status_value != AppointmentStatus.CANCELLED:
            return Response({"detail": "امکان تغییر وضعیت به مقدار درخواستی وجود ندارد."}, status=status.HTTP_400_BAD_REQUEST)

        client_profile = getattr(request.user, "client_profile", None)
        if client_profile != instance.client:
            return Response({"detail": "فقط موکل می‌تواند رزرو را لغو کند."}, status=status.HTTP_403_FORBIDDEN)

        instance.status = AppointmentStatus.CANCELLED
        instance.save(update_fields=["status"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
