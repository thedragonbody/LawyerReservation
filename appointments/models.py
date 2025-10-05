from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import LawyerProfile, ClientProfile
from common.models import BaseModel
from common.choices import AppointmentStatus, SessionType
from common.validators import validate_slot_time
from decimal import Decimal

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