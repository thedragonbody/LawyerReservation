from django.contrib import admin
from .models import OTPRecord


@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display = ('phone', 'code', 'is_used', 'attempts', 'created_at', 'expires_at')
    list_filter = ('is_used',)
    search_fields = ('phone',)
    readonly_fields = ('created_at',)
