from django.contrib import admin
from .models import LawyerProfile, PracticeArea, Education, Availability, Review


class PracticeAreaInline(admin.TabularInline):
    model = PracticeArea
    extra = 1


class EducationInline(admin.TabularInline):
    model = Education
    extra = 1


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 0


@admin.register(LawyerProfile)
class LawyerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bar_number', 'verification_status', 'is_accepting_clients',
                    'average_rating', 'total_bookings', 'is_featured')
    list_filter = ('verification_status', 'is_accepting_clients', 'is_featured')
    search_fields = ('user__first_name', 'user__last_name', 'bar_number')
    inlines = [PracticeAreaInline, EducationInline, AvailabilityInline]
    actions = ['verify_lawyers', 'feature_lawyers']

    @admin.action(description='Verify selected lawyers')
    def verify_lawyers(self, request, queryset):
        queryset.update(verification_status='verified')

    @admin.action(description='Feature selected lawyers')
    def feature_lawyers(self, request, queryset):
        queryset.update(is_featured=True)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('lawyer', 'customer', 'rating', 'is_anonymous', 'created_at')
    list_filter = ('rating',)
