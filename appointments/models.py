from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
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
    def cancel(self, user=None, calendar_service=None, *, force=False, send_notifications=False):
        # فقط کاربر می‌تواند لغو کند و تا 24 ساعت قبل مگر اینکه force فعال باشد
        if not force:
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

        if send_notifications:
            self._send_cancellation_notifications()

        return sync_result

    def cancel_by_system(self, calendar_service=None):
        return self.cancel(
            calendar_service=calendar_service,
            force=True,
            send_notifications=True,
        )

    def _send_cancellation_notifications(self):
        client_user = self.client.user
        lawyer_user = self.lawyer.user
        appointment_time = timezone.localtime(self.slot.start_time)
        appointment_time_str = appointment_time.strftime("%Y-%m-%d %H:%M")
        client_name = client_user.get_full_name() or client_user.phone_number
        lawyer_name = lawyer_user.get_full_name() or lawyer_user.phone_number

        try:
            Notification.objects.create(
                user=client_user,
                appointment=self,
                title="رزرو لغو شد",
                message=(
                    f"رزروی که برای {appointment_time_str} با {lawyer_name} داشتید، لغو شد."
                ),
            )
            Notification.objects.create(
                user=lawyer_user,
                appointment=self,
                title="رزرو کاربر لغو شد",
                message=(
                    f"{client_name} رزروی که داشت را برای {appointment_time_str} لغو کرد."
                ),
            )
        except Exception:
            pass

        try:
            send_sms(
                client_user.phone_number,
                f"رزرو شما برای {appointment_time_str} لغو شد.",
            )
            send_sms(
                lawyer_user.phone_number,
                f"رزرو کاربر {client_name} برای {appointment_time_str} لغو شد.",
            )
        except Exception:
            pass

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
class OnsiteSlot(BaseModel):
    lawyer = models.ForeignKey(
        LawyerProfile, on_delete=models.CASCADE, related_name="onsite_slots"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    office_address = models.CharField(max_length=255, blank=True)
    office_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    office_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    is_booked = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_time"]
        unique_together = ("lawyer", "start_time", "end_time")

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")

    def __str__(self):
        return (
            f"{self.lawyer.user.get_full_name()} | {self.start_time} - {self.end_time}"
        )


class OnsiteAppointment(BaseModel):
    lawyer = models.ForeignKey(
        LawyerProfile, on_delete=models.CASCADE, related_name="onsite_appointments"
    )
    client = models.ForeignKey(
        ClientProfile, on_delete=models.CASCADE, related_name="onsite_appointments"
    )
    slot = models.ForeignKey(
        OnsiteSlot, on_delete=models.CASCADE, related_name="appointments"
    )
    status = models.CharField(
        max_length=10, choices=AppointmentStatus.choices, default=AppointmentStatus.PENDING
    )
    office_address = models.CharField(max_length=255, blank=True)
    office_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    office_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["slot__start_time"]

    def __str__(self):
        return (
            f"{self.client.user.get_full_name()} -> {self.lawyer.user.get_full_name()}"
            f" | {self.slot.start_time} | {self.status}"
        )


@receiver(pre_save, sender=OnsiteSlot)
def ensure_valid_onsite_slot(sender, instance, **kwargs):
    """Prevent overlapping slots for the same lawyer and ensure office info."""

    if instance.lawyer:
        if not instance.office_address:
            instance.office_address = instance.lawyer.office_address or ""
        if instance.office_latitude is None:
            instance.office_latitude = instance.lawyer.office_latitude
        if instance.office_longitude is None:
            instance.office_longitude = instance.lawyer.office_longitude

    if instance.end_time <= instance.start_time:
        raise ValidationError("End time must be after start time.")

    overlapping = OnsiteSlot.objects.filter(
        lawyer=instance.lawyer,
        start_time__lt=instance.end_time,
        end_time__gt=instance.start_time,
    )
    if instance.pk:
        overlapping = overlapping.exclude(pk=instance.pk)
    if overlapping.exists():
        raise ValidationError("این بازه زمانی با اسلات دیگری تداخل دارد.")


@receiver(pre_save, sender=OnsiteAppointment)
def prevent_double_booking(sender, instance, **kwargs):
    """Ensure a slot is not booked by more than one appointment."""

    if not instance.slot_id:
        return

    active_qs = OnsiteAppointment.objects.filter(slot=instance.slot).exclude(
        pk=instance.pk
    )
    active_qs = active_qs.exclude(status=AppointmentStatus.CANCELLED)
    if active_qs.exists() and instance.status != AppointmentStatus.CANCELLED:
        raise ValidationError("این اسلات قبلاً رزرو شده است.")

    # Populate office info from slot if not provided
    if not instance.office_address:
        instance.office_address = instance.slot.office_address
    if instance.office_latitude is None:
        instance.office_latitude = instance.slot.office_latitude
    if instance.office_longitude is None:
        instance.office_longitude = instance.slot.office_longitude


def _sync_slot_booking_state(slot):
    """Helper to mark a slot as booked when active appointments exist."""

    if not getattr(slot, "pk", None):
        return

    has_active = slot.appointments.exclude(
        status=AppointmentStatus.CANCELLED
    ).exists()
    if slot.is_booked != has_active:
        slot.is_booked = has_active
        slot.save(update_fields=["is_booked"])


@receiver(post_save, sender=OnsiteAppointment)
def mark_slot_booked(sender, instance, **kwargs):
    _sync_slot_booking_state(instance.slot)


@receiver(post_delete, sender=OnsiteAppointment)
def release_slot_on_delete(sender, instance, **kwargs):
    _sync_slot_booking_state(instance.slot)
