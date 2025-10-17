from django.contrib import admin
from .models import Slot, Appointment
from django.utils.html import format_html
from urllib.parse import quote

@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ['id', 'lawyer', 'start_time', 'end_time', 'is_booked', 'price']
    list_filter = ['lawyer', 'is_booked']

class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'lawyer', 'slot', 'status', 'location', 'view_map_link']
    list_filter = ['status', 'lawyer']
    search_fields = ['client__user__username', 'lawyer__user__username', 'location']

    readonly_fields = ('view_map_link',)

    def view_map_link(self, obj):
        if obj.location:
            url = f"https://www.google.com/maps/search/?api=1&query={quote(obj.location)}"
            return format_html(f'<a href="{url}" target="_blank">📍 نمایش روی نقشه</a>')
        return "-"
    view_map_link.short_description = "Map Link"