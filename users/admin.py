from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ClientProfile, LawyerProfile

# ================= UserAdmin =================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'phone_number', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'phone_number', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'phone_number', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone_number', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

# ================= ClientProfileAdmin =================
@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'national_id', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'national_id')

# ================= LawyerProfileAdmin =================
@admin.register(LawyerProfile)
class LawyerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'degree', 'experience_years', 'status', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'degree', 'expertise')
    list_filter = ('status',)