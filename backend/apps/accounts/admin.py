from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone', 'full_name', 'role', 'is_phone_verified', 'is_active', 'created_at')
    list_filter = ('role', 'is_phone_verified', 'is_active')
    search_fields = ('phone', 'first_name', 'last_name')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal', {'fields': ('first_name', 'last_name', 'avatar')}),
        ('Role & Status', {'fields': ('role', 'is_phone_verified', 'is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
