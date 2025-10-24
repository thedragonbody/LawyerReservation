from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from client_profile.models import ClientProfile
from common.choices import AppointmentStatus
from common.models import BaseModel
from common.utils import send_sms
from lawyer_profile.models import LawyerProfile
from notifications.models import Notification

from .integrations import CalendarService, CalendarSyncError, CalendarSyncResult

class OnlineSlot(BaseModel):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='online_slots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=500000)

    class Meta:
        ordering = ['start_time']
        unique_together = ('lawyer', 'start_time', 'end_time')

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")

    def __str__(self):
        return f"{self.lawyer.user.get_full_name()} | {self.start_time} - {self.end_time} | Booked: {self.is_booked}"


class OnlineAppointment(BaseModel):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='online_appointments')
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='online_appointments')
    slot = models.ForeignKey(OnlineSlot, on_delete=models.CASCADE, related_name='appointments')
    status = models.CharField(max_length=10, choices=AppointmentStatus.choices, default=AppointmentStatus.PENDING)
    google_meet_link = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    is_reminder_sent = models.BooleanField(default=False)
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['slot__start_time']

    def __str__(self):
        return f"{self.client.user.get_full_name()} -> {self.lawyer.user.get_full_name()} | {self.slot.start_time} | {self.status}"

    # -----------------------------
    # عملیات رزرو با race condition
    # -----------------------------
    def confirm(self, calendar_service=None, **kwargs):
        if self.status == AppointmentStatus.CONFIRMED:
            return CalendarSyncResult(success=True, event_id=self.calendar_event_id)

        # محدودیت 1 رزرو در روز
        today = self.slot.start_time.date()
        existing = OnlineAppointment.objects.filter(client=self.client, slot__start_time__date=today, status=AppointmentStatus.CONFIRMED)
        if existing.exists():
            raise ValidationError("شما فقط می‌توانید یک رزرو آنلاین در روز داشته باشید.")

        with transaction.atomic():
            slot_qs = OnlineSlot.objects.select_for_update().filter(pk=self.slot.pk)
            slot = slot_qs.get()
            if slot.is_booked:
                raise ValidationError("این اسلات قبلا رزرو شده است.")
            slot.is_booked = True
            slot.save(update_fields=["is_booked"])

            self.status = AppointmentStatus.CONFIRMED
            self.google_meet_link = self.create_google_meet_link()
            self.save(update_fields=["status", "google_meet_link"])

        calendar_service = calendar_service or CalendarService()
        sync_result = CalendarSyncResult(success=True, event_id=self.calendar_event_id)
        try:
            event_id = calendar_service.create_event(self)
        except CalendarSyncError as exc:
            sync_result = CalendarSyncResult(success=False, message=str(exc), event_id=self.calendar_event_id)
        else:
            if event_id and event_id != self.calendar_event_id:
                self.calendar_event_id = event_id
                self.save(update_fields=["calendar_event_id"])
                sync_result = CalendarSyncResult(success=True, event_id=event_id)

        # ارسال اتوماتیک Notification و SMS
        self.send_notifications()
        return sync_result

    # -----------------------------
    # Cancel / Reschedule
    # -----------------------------
    def cancel(self, user=None, calendar_service=None, **kwargs):
        # فقط کاربر می‌تواند لغو کند و تا 24 ساعت قبل
        if user and user != self.client.user:
            raise ValidationError("فقط کاربر می‌تواند لغو کند.")
        if self.slot.start_time - timezone.now() < timedelta(hours=24):
            raise ValidationError("لغو رزرو تنها تا 24 ساعت قبل امکان‌پذیر است.")
        if self.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
            return CalendarSyncResult(success=True, event_id=self.calendar_event_id)

        with transaction.atomic():
            slot_qs = OnlineSlot.objects.select_for_update().filter(pk=self.slot.pk)
            slot = slot_qs.get()
            slot.is_booked = False
            slot.save(update_fields=["is_booked"])

            self.status = AppointmentStatus.CANCELLED
            self.save(update_fields=["status"])
        calendar_service = calendar_service or CalendarService()
        sync_result = CalendarSyncResult(success=True, event_id=self.calendar_event_id)
        try:
            calendar_service.delete_event(self)
        except CalendarSyncError as exc:
            sync_result = CalendarSyncResult(success=False, message=str(exc), event_id=self.calendar_event_id)
        else:
            if self.calendar_event_id:
                self.calendar_event_id = None
                self.save(update_fields=["calendar_event_id"])
                sync_result = CalendarSyncResult(success=True, event_id=None)

        return sync_result

    # -----------------------------
    # ایجاد لینک Google Meet
    # -----------------------------
    def create_google_meet_link(self):
        """
        این تابع باید از Google Calendar API برای ایجاد meeting استفاده کند
        """
        # مثال ساده برای تست (واقعی باید با API ارتباط برقرار شود)
        return f"https://meet.google.com/{self.id}-{self.client.id}"

    # -----------------------------
    # Notification / SMS
    # -----------------------------
    def send_notifications(self):
        try:
            Notification.objects.create(
                user=self.client.user,
                appointment=self,
                title="رزرو آنلاین تایید شد",
                message=f"جلسه شما با {self.lawyer.user.get_full_name()} تایید شد. لینک گوگل میت: {self.google_meet_link}"
            )
            Notification.objects.create(
                user=self.lawyer.user,
                appointment=self,
                title="رزرو آنلاین تایید شد",
                message=f"جلسه با {self.client.user.get_full_name()} تایید شد. لینک گوگل میت: {self.google_meet_link}"
            )
            send_sms(self.client.user.phone_number, f"رزرو آنلاین شما با {self.lawyer.user.get_full_name()} تایید شد. لینک: {self.google_meet_link}")
            send_sms(self.lawyer.user.phone_number, f"رزرو آنلاین با {self.client.user.get_full_name()} تایید شد. لینک: {self.google_meet_link}")
        except Exception as e:
            print(f"[Warning] Failed to send notification or SMS: {e}")
