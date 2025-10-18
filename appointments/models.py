from django.db import models, transaction
from lawyer_profile.models import LawyerProfile
from client_profile.models import ClientProfile
from common.models import BaseModel
from common.choices import AppointmentStatus
from common.validators import validate_slot_time
from django.core.exceptions import ObjectDoesNotExist
from notifications.models import Notification
from common.utils import send_sms

class Slot(BaseModel):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='slots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=500000)

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
    status = models.CharField(max_length=10, choices=AppointmentStatus.choices, default=AppointmentStatus.PENDING)
    description = models.TextField(blank=True)
    rescheduled_from = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True)
    @property
    def location_name(self):
        return self.lawyer.office_location or "آدرس ثبت نشده"
    
    class Meta:
        ordering = ['slot__start_time']

    def __str__(self):
        return f"{self.client.user.get_full_name()} -> {self.lawyer.user.get_full_name()} | {self.slot.start_time} | {self.status}"

    # -----------------------------
    # عملیات رزرو، لغو و تکمیل
    # -----------------------------
    def confirm(self) -> bool:
        if self.status == AppointmentStatus.CONFIRMED:
            return False

        with transaction.atomic():
            slot_qs = type(self.slot).objects.select_for_update().filter(pk=self.slot.pk)
            slot = slot_qs.get()

            if not slot.is_booked:
                slot.is_booked = True
                slot.save(update_fields=["is_booked"])

            self.status = AppointmentStatus.CONFIRMED
            self.save(update_fields=["status"])

        try:
            Notification.objects.create(
                user=self.client.user,
                appointment=self,
                title="Appointment Confirmed",
                message=f"جلسه شما با {self.lawyer.user.get_full_name()} تأیید شد."
            )
            send_sms(
                self.client.user.phone_number,
                f"وقت شما {self.slot.start_time} با {self.lawyer.user.get_full_name()} تایید شد."
            )
        except Exception as e:
            print(f"[Warning] Failed to send notification or SMS: {e}")

        return True

    def cancel(self) -> bool:
        if self.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
            return False

        with transaction.atomic():
            slot_qs = type(self.slot).objects.select_for_update().filter(pk=self.slot.pk)
            slot = slot_qs.get()

            if slot.is_booked:
                slot.is_booked = False
                slot.save(update_fields=["is_booked"])

            self.status = AppointmentStatus.CANCELLED
            self.save(update_fields=["status"])

        return True

    def complete(self) -> bool:
        if self.status == AppointmentStatus.COMPLETED:
            return False
        self.status = AppointmentStatus.COMPLETED
        self.save(update_fields=["status"])
        return True