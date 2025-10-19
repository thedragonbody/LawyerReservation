from django.contrib import admin
from .models import OnlineAppointment  # بجای Appointment و Slot

@admin.register(OnlineAppointment)
class OnlineAppointmentAdmin(admin.ModelAdmin):
    list_display = ('client', 'lawyer', 'start_time', 'status')
    search_fields = ('client__user__email', 'lawyer__user__email')