from django.contrib import admin
from .models import Slot, Appointment
from django.utils.html import format_html
from urllib.parse import quote

@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ['id', 'lawyer', 'start_time', 'end_time', 'is_booked', 'price']
    list_filter = ['lawyer', 'is_booked']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'lawyer', 'slot', 'status', 'get_office_address']
    def get_office_address(self, obj):
        return obj.slot.lawyer.office_address
    get_office_address.short_description = 'Office Address'