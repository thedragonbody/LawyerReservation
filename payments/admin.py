from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'appointment', 'amount', 'payment_method', 'status', 'transaction_id', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('user__email', 'transaction_id')