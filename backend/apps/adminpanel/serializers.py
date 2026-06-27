from rest_framework import serializers
from apps.accounts.models import User
from apps.lawyers.models import LawyerProfile, PracticeArea, Review
from apps.bookings.models import Booking, BookingDocument, BookingCancellationLog
from .models import CommissionSetting, DiscountCode, LawyerSettlement, SiteContent


PRACTICE_AREA_FA = {
    'corporate': 'حقوق شرکت‌ها',
    'criminal': 'کیفری و جزایی',
    'family': 'خانواده و طلاق',
    'immigration': 'مهاجرت',
    'intellectual_property': 'مالکیت فکری',
    'real_estate': 'ملک و املاک',
    'employment': 'حقوق کار و استخدام',
    'tax': 'حقوق مالیاتی',
    'personal_injury': 'خسارت و دیه',
    'bankruptcy': 'ورشکستگی',
    'civil_litigation': 'دعاوی حقوقی',
    'estate_planning': 'وصیت و ارث',
    'healthcare': 'حقوق پزشکی و سلامت',
    'environmental': 'حقوق محیط زیست',
    'international': 'حقوق بین‌الملل',
}


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'phone', 'first_name', 'last_name', 'full_name',
            'role', 'is_active', 'is_staff', 'is_phone_verified',
            'avatar_url', 'created_at',
        )

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class AdminLawyerSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    bar_document_url = serializers.SerializerMethodField()
    primary_area = serializers.SerializerMethodField()
    practice_areas_fa = serializers.SerializerMethodField()

    class Meta:
        model = LawyerProfile
        fields = (
            'id', 'user_id', 'full_name', 'phone', 'avatar_url',
            'bar_number', 'bar_document_url', 'headline', 'bio',
            'years_experience', 'consultation_fee', 'city', 'office_address',
            'verification_status', 'is_accepting_clients', 'is_featured',
            'average_rating', 'total_reviews', 'total_bookings',
            'primary_area', 'practice_areas_fa', 'created_at', 'updated_at',
        )

    def get_avatar_url(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
            return obj.user.avatar.url
        return None

    def get_bar_document_url(self, obj):
        if obj.bar_document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.bar_document.url)
            return obj.bar_document.url
        return None

    def get_primary_area(self, obj):
        pa = obj.practice_areas.filter(is_primary=True).first()
        return PRACTICE_AREA_FA.get(pa.area, pa.get_area_display()) if pa else ''

    def get_practice_areas_fa(self, obj):
        return [PRACTICE_AREA_FA.get(pa.area, pa.get_area_display()) for pa in obj.practice_areas.all()]


class AdminBookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    lawyer_name = serializers.CharField(source='lawyer.user.full_name', read_only=True)
    lawyer_phone = serializers.CharField(source='lawyer.user.phone', read_only=True)
    lawyer_id = serializers.UUIDField(source='lawyer.id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_booking_type_display', read_only=True)
    scheduled_at_display = serializers.SerializerMethodField()
    documents_count = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'customer_name', 'customer_phone', 'lawyer_name', 'lawyer_phone', 'lawyer_id',
            'booking_type', 'type_display', 'status', 'status_display',
            'scheduled_at', 'scheduled_at_display', 'duration_minutes',
            'subject', 'description', 'practice_area', 'meeting_link', 'meeting_location',
            'rejection_reason', 'documents_count', 'created_at',
        )

    def get_scheduled_at_display(self, obj):
        from django.utils import timezone
        if not obj.scheduled_at:
            return ''
        return timezone.localtime(obj.scheduled_at).strftime('%Y-%m-%d %H:%M')

    def get_documents_count(self, obj):
        return obj.documents.count()


class AdminBookingDocumentSerializer(serializers.ModelSerializer):
    booking_id = serializers.UUIDField(source='booking.id', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = BookingDocument
        fields = (
            'id', 'booking_id', 'uploaded_by_name', 'document_type', 'title',
            'file_url', 'file_size', 'mime_type', 'is_confidential', 'uploaded_at',
        )

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None



class AdminReviewSerializer(serializers.ModelSerializer):
    lawyer_name = serializers.CharField(source='lawyer.user.full_name', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)

    class Meta:
        model = Review
        fields = (
            'id', 'lawyer', 'lawyer_name', 'customer', 'customer_name', 'customer_phone',
            'rating', 'comment', 'is_anonymous', 'created_at',
        )


class AdminRevenueItemSerializer(serializers.Serializer):
    booking_id = serializers.CharField()
    lawyer_name = serializers.CharField()
    customer_name = serializers.CharField()
    amount = serializers.IntegerField()
    status = serializers.CharField()
    scheduled_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()


class AdminCancellationLogSerializer(serializers.ModelSerializer):
    booking_subject = serializers.CharField(source='booking.subject', read_only=True)
    customer_name = serializers.CharField(source='booking.customer.full_name', read_only=True)
    lawyer_name = serializers.CharField(source='booking.lawyer.user.full_name', read_only=True)

    class Meta:
        model = BookingCancellationLog
        fields = (
            'id', 'booking', 'booking_subject', 'customer_name', 'lawyer_name',
            'reason', 'hours_before_session', 'refund_amount', 'cancellation_fee',
            'refund_status', 'admin_note', 'created_at',
        )


class CommissionSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionSetting
        fields = ('id', 'title', 'commission_percent', 'is_active', 'updated_at')


class DiscountCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountCode
        fields = ('id', 'code', 'percent', 'amount', 'is_active', 'usage_limit', 'used_count', 'starts_at', 'ends_at', 'created_at')


class LawyerSettlementSerializer(serializers.ModelSerializer):
    lawyer_name = serializers.CharField(source='lawyer.user.full_name', read_only=True)
    lawyer_phone = serializers.CharField(source='lawyer.user.phone', read_only=True)

    class Meta:
        model = LawyerSettlement
        fields = ('id', 'lawyer', 'lawyer_name', 'lawyer_phone', 'amount', 'commission_amount', 'net_amount', 'status', 'note', 'paid_at', 'created_at')


class SiteContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteContent
        fields = ('id', 'key', 'title', 'body', 'is_active', 'updated_at')
