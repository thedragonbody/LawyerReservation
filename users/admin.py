from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from client_profile.models import ClientProfile
from lawyer_profile.models import LawyerProfile

# Inlines برای پروفایل‌ها
class ClientProfileInline(admin.StackedInline):
    model = ClientProfile
    can_delete = False
    verbose_name_plural = 'Client Profile'
    fk_name = 'user'

class LawyerProfileInline(admin.StackedInline):
    model = LawyerProfile
    can_delete = False
    verbose_name_plural = 'Lawyer Profile'
    fk_name = 'user'

# Admin اصلی برای User
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "phone_number",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("phone_number", "first_name", "last_name")
    ordering = ("id",)
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "password1", "password2", "is_active", "is_staff"),
        }),
    )
    inlines = [ClientProfileInline, LawyerProfileInline]
    filter_horizontal = ("groups", "user_permissions")