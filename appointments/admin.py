from django.contrib import admin
from .models import Slot, Appointment

@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ['id', 'lawyer', 'start_time', 'end_time', 'is_booked']
    list_filter = ['lawyer', 'is_booked']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'lawyer', 'slot', 'session_type', 'status']
    list_filter = ['status', 'session_type', 'lawyer']
    search_fields = ['client__user__username', 'lawyer__user__username']