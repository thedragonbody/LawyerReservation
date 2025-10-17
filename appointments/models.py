from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from users.models import LawyerProfile, ClientProfile
from common.models import BaseModel
from common.choices import AppointmentStatus, SessionType
from common.validators import validate_slot_time
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from appointments.utils import create_meeting_link
from notifications.models import Notification
from common.utils import send_sms
from django.db.models import Prefetch

class Slot(BaseModel):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='slots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=500000)  # 500,000 ریال ثابت

    class Meta:
        ordering = ['start_time']
        unique_together = ('lawyer', 'start_time', 'end_time')

    def clean(self):
        validate_slot_time(self.start_time, self.end_time)

    def __str__(self):
        return f"{self.lawyer.user.get_full_name()} | {self.start_time} - {self.end_time} | Booked: {self.is_booked} | Price: {self.price}"

class Appointment(BaseModel):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='appointments')
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='appointments')
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name='appointments')
    session_type = models.CharField(max_length=10, choices=SessionType.choices)
    status = models.CharField(max_length=10, choices=AppointmentStatus.choices, default=AppointmentStatus.PENDING)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    online_link = models.URLField(blank=True, null=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    rescheduled_from = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['slot__start_time']

    def __str__(self):
        return f"{self.client.user.get_full_name()} -> {self.lawyer.user.get_full_name()} | {self.slot.start_time} | {self.status}"

    # -----------------------------
    # Helper methods for state changes
    # -----------------------------


    def confirm(self, transaction_id: str = None) -> bool:
        """
        Confirm this appointment atomically:
        - Locks the related slot row to avoid race conditions
        - Marks slot.is_booked = True (if not already booked)
        - Sets appointment.status = CONFIRMED
        - Optionally sets transaction_id
        - Creates an online meeting link ONLY if session_type == ONLINE
        - Sends notification & SMS if applicable
        Returns True if a state change occurred (i.e. was confirmed now), False if already confirmed.
        """
        # 🧩 اگر از قبل تأیید شده باشد، هیچ کاری نکن
        if self.status == AppointmentStatus.CONFIRMED:
            return False

        with transaction.atomic():
            # 🔒 قفل‌کردن Slot برای جلوگیری از رزرو هم‌زمان
            slot_qs = type(self.slot).objects.select_for_update().filter(pk=self.slot.pk)
            try:
                slot = slot_qs.get()
            except ObjectDoesNotExist:
                raise

            # 📅 اگر هنوز رزرو نشده، رزروش کن
            if not slot.is_booked:
                slot.is_booked = True
                slot.save(update_fields=["is_booked"])

            # 🔁 تغییر وضعیت به Confirmed فقط در صورت نیاز
            if self.status != AppointmentStatus.CONFIRMED:
                self.status = AppointmentStatus.CONFIRMED
                fields_to_update = ["status"]

                # 💳 ثبت شماره تراکنش در صورت وجود
                if transaction_id:
                    self.transaction_id = transaction_id
                    fields_to_update.append("transaction_id")

                # 💻 ساخت لینک فقط برای جلسات آنلاین
                if self.session_type == SessionType.ONLINE:
                    self.online_link = create_meeting_link(self)
                    fields_to_update.append("online_link")

                # 💾 ذخیره تغییرات
                self.save(update_fields=fields_to_update)

        # 🚀 پس از commit، ارسال نوتیف و پیامک (خارج از transaction)
        if self.session_type == SessionType.ONLINE and self.online_link:
            try:
                # 📲 ایجاد نوتیف در سیستم
                Notification.objects.create(
                    user=self.client.user,
                    appointment=self,
                    title="لینک جلسه آنلاین شما آماده است",
                    message=f"جلسه شما با {self.lawyer.user.get_full_name()} تأیید شد.\n"
                            f"لینک ورود: {self.online_link}"
                )

                # 📤 ارسال پیامک برای کاربر
                send_sms(
                    self.client.user.phone_number,
                    f"جلسه آنلاین شما با {self.lawyer.user.get_full_name()} تأیید شد.\n"
                    f"لینک ورود: {self.online_link}"
                )
            except Exception as e:
                # از شکست ارسال پیامک جلوگیری می‌کنیم تا تراکنش تأیید نشود
                print(f"[Warning] Failed to send notification or SMS: {e}")

        return True
        

    def cancel(self, cancellation_reason: str = None, refund: bool = False) -> bool:
        """
        Cancel this appointment atomically:
        - If already cancelled/completed => no-op (idempotent)
        - Sets appointment.status = CANCELLED
        - Frees the slot (is_booked = False) if it was booked
        - Optionally record cancellation_reason
        - return True if state changed (i.e. was cancelled now), False if no change
        Note: refund handling (i.e. changing Payment.status) should be done in view or signal.
        If refund=True this method does NOT modify Payment objects directly, but you can add logic in your payment app.
        """
        # If already cancelled or completed, do nothing
        if self.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
            return False

        with transaction.atomic():
            # lock slot row
            slot_qs = type(self.slot).objects.select_for_update().filter(pk=self.slot.pk)
            try:
                slot = slot_qs.get()
            except ObjectDoesNotExist:
                raise

            # free slot if booked
            if slot.is_booked:
                slot.is_booked = False
                slot.save(update_fields=["is_booked"])

            # update appointment
            self.status = AppointmentStatus.CANCELLED
            if cancellation_reason:
                self.cancellation_reason = cancellation_reason
                self.save(update_fields=["status", "cancellation_reason"])
            else:
                self.save(update_fields=["status"])

            # Note: we intentionally do not touch Payment model here to keep responsibilities separate.
            # If you want, your payments.cancel flow or payment signals can handle Payment.status -> REFUNDED.
            return True

    def complete(self) -> bool:
        """
        Mark appointment as completed (e.g. after session finished).
        Idempotent: returns False if already COMPLETED.
        """
        if self.status == AppointmentStatus.COMPLETED:
            return False
        self.status = AppointmentStatus.COMPLETED
        self.save(update_fields=["status"])
        return True
    
    def get_queryset(self):
        qs = Appointment.objects.select_related(
            "client",
            "client__user",
            "lawyer",
            "lawyer__user",
            "slot"
        )
        # اگر نیاز به فیلتر یا ordering دارید اضافه کنید
        return qs.order_by("-slot__start_time")