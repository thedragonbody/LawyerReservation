from django.contrib import admin
from .models import Booking, BookingDocument


class BookingDocumentInline(admin.TabularInline):
    model = BookingDocument
    extra = 0
    readonly_fields = ('file_size', 'mime_type', 'uploaded_at')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('subject', 'customer', 'lawyer', 'status', 'booking_type', 'scheduled_at', 'created_at')
    list_filter = ('status', 'booking_type')
    search_fields = ('subject', 'customer__first_name', 'customer__last_name', 'lawyer__user__first_name')
    inlines = [BookingDocumentInline]
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(BookingDocument)
class BookingDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'document_type', 'booking', 'uploaded_by', 'file_size', 'uploaded_at')
    list_filter = ('document_type', 'is_confidential')
