from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from client_profile.models import ClientProfile
from common.choices import AppointmentStatus, SessionType
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


class InPersonAppointment(BaseModel):
    lawyer = models.ForeignKey(
        LawyerProfile,
        on_delete=models.CASCADE,
        related_name="inperson_appointments",
    )
    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="inperson_appointments",
    )
    scheduled_for = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.PENDING,
    )
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["scheduled_for"]

    def __str__(self):
        start_time = timezone.localtime(self.scheduled_for)
        return (
            f"جلسه حضوری {self.client.user.get_full_name()} با "
            f"{self.lawyer.user.get_full_name()} در {start_time:%Y-%m-%d %H:%M}"
        )

    @property
    def session_type(self):
        return SessionType.OFFLINE

    def mark_payment_completed(self):
        updated_fields = []
        if self.status != AppointmentStatus.PAID:
            self.status = AppointmentStatus.PAID
            updated_fields.append("status")
        if updated_fields:
            self.save(update_fields=updated_fields)
        self._send_payment_notification(is_refund=False)

    def mark_payment_refunded(self):
        updated_fields = []
        if self.status != AppointmentStatus.PENDING:
            self.status = AppointmentStatus.PENDING
            updated_fields.append("status")
        if updated_fields:
            self.save(update_fields=updated_fields)
        self._send_payment_notification(is_refund=True)

    def _send_payment_notification(self, *, is_refund: bool):
        event_time = timezone.localtime(self.scheduled_for).strftime("%Y-%m-%d %H:%M")
        lawyer_name = self.lawyer.user.get_full_name() or self.lawyer.user.phone_number
        client_name = self.client.user.get_full_name() or self.client.user.phone_number

        if is_refund:
            client_title = "بازگشت وجه رزرو حضوری"
            lawyer_title = "بازگشت وجه جلسه حضوری"
            client_message = (
                f"مبلغ پرداختی شما برای جلسه حضوری با {lawyer_name} در تاریخ {event_time} بازگشت داده شد."
            )
            lawyer_message = (
                f"مبلغ جلسه حضوری با {client_name} در تاریخ {event_time} به کاربر بازگردانده شد."
            )
            notification_type = Notification.Type.INPERSON_PAYMENT_REFUNDED
        else:
            client_title = "پرداخت جلسه حضوری تایید شد"
            lawyer_title = "پرداخت جلسه حضوری جدید"
            client_message = (
                f"پرداخت شما برای جلسه حضوری با {lawyer_name} در تاریخ {event_time} با موفقیت ثبت شد."
            )
            lawyer_message = (
                f"پرداخت جلسه حضوری با {client_name} در تاریخ {event_time} با موفقیت انجام شد."
            )
            notification_type = Notification.Type.INPERSON_PAYMENT_SUCCESS

        Notification.send(
            user=self.client.user,
            title=client_title,
            message=client_message,
            type_=notification_type,
        )
        Notification.send(
            user=self.lawyer.user,
            title=lawyer_title,
            message=lawyer_message,
            type_=notification_type,
        )

        send_sms(self.client.user.phone_number, client_message)
        send_sms(self.lawyer.user.phone_number, lawyer_message)
