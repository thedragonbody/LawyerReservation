from rest_framework import serializers
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Booking, BookingDocument, BookingCancellationLog
from apps.lawyers.serializers import LawyerListSerializer
from apps.accounts.serializers import UserSerializer


class BookingDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)

    class Meta:
        model = BookingDocument
        fields = ('id', 'document_type', 'document_type_display', 'title',
                  'file_url', 'file_size', 'mime_type', 'is_confidential', 'uploaded_at')
        read_only_fields = ('file_size', 'mime_type', 'uploaded_at')

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class UploadDocumentSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=BookingDocument.DOCUMENT_TYPES)
    title = serializers.CharField(max_length=200)
    file = serializers.FileField()
    is_confidential = serializers.BooleanField(default=True)

    def validate_file(self, value):
        allowed = getattr(settings, 'ALLOWED_DOCUMENT_TYPES', [])
        if allowed and value.content_type not in allowed:
            raise serializers.ValidationError(
                f'File type not allowed. Allowed: PDF, JPG, PNG, WEBP, DOC, DOCX'
            )
        max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 20 * 1024 * 1024)
        if value.size > max_size:
            raise serializers.ValidationError(f'File too large. Max size is 20MB.')
        return value


class BookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    lawyer_name = serializers.CharField(source='lawyer.user.full_name', read_only=True)
    lawyer_id = serializers.UUIDField(source='lawyer.id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_booking_type_display', read_only=True)
    scheduled_at_display = serializers.SerializerMethodField()
    scheduled_time = serializers.SerializerMethodField()
    documents = BookingDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = (
            'id', 'customer_name', 'lawyer_name', 'lawyer_id',
            'booking_type', 'type_display', 'status', 'status_display',
            'scheduled_at', 'scheduled_at_display', 'scheduled_time', 'duration_minutes', 'subject', 'description',
            'practice_area', 'meeting_link', 'meeting_location',
            'rejection_reason', 'refund_status', 'refund_amount', 'cancellation_fee',
            'cancelled_at', 'cancellation_reason', 'refund_note', 'documents', 'created_at',
        )
        read_only_fields = ('status', 'lawyer_notes', 'rejection_reason', 'meeting_link')

    def get_scheduled_at_display(self, obj):
        if not obj.scheduled_at:
            return ''
        local_dt = timezone.localtime(obj.scheduled_at)
        return local_dt.strftime('%Y-%m-%d %H:%M')

    def get_scheduled_time(self, obj):
        if not obj.scheduled_at:
            return ''
        return timezone.localtime(obj.scheduled_at).strftime('%H:%M')


class CreateBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ('lawyer', 'booking_type', 'scheduled_at', 'duration_minutes',
                  'subject', 'description', 'practice_area')

    def validate_lawyer(self, value):
        if not value.is_accepting_clients:
            raise serializers.ValidationError('این وکیل در حال حاضر پذیرش موکل جدید ندارد.')
        if value.verification_status != 'verified':
            raise serializers.ValidationError('این وکیل هنوز توسط ادمین تایید نشده است.')
        return value

    def validate(self, attrs):
        scheduled_at = attrs.get('scheduled_at')
        lawyer = attrs.get('lawyer')
        duration = attrs.get('duration_minutes') or 60
        subject = str(attrs.get('subject') or '').strip()
        description = str(attrs.get('description') or '').strip()

        if not subject:
            raise serializers.ValidationError({'subject': 'عنوان پرونده الزامی است.'})

        if not description or len(description) < 10:
            raise serializers.ValidationError({'description': 'شرح مشکل باید حداقل ۱۰ کاراکتر باشد.'})

        if scheduled_at:
            min_date = (timezone.localdate() + timedelta(days=3))
            if scheduled_at.date() < min_date:
                raise serializers.ValidationError({'scheduled_at': 'رزرو فقط از ۳ روز بعد امکان‌پذیر است.'})

        if lawyer and scheduled_at:
            exists = Booking.objects.filter(
                lawyer=lawyer,
                scheduled_at=scheduled_at,
                status__in=['pending', 'confirmed'],
            ).exists()
            if exists:
                raise serializers.ValidationError({'scheduled_at': 'این ساعت قبلاً رزرو شده است.'})

        return attrs


class LawyerBookingUpdateSerializer(serializers.ModelSerializer):
    """Lawyer updates status, adds notes, meeting link."""
    class Meta:
        model = Booking
        fields = ('status', 'lawyer_notes', 'rejection_reason', 'meeting_link', 'meeting_location')

    def validate_status(self, value):
        allowed = ['confirmed', 'rejected', 'completed']
        if value not in allowed:
            raise serializers.ValidationError(f'Lawyer can only set status to: {", ".join(allowed)}')
        return value


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class BookingCancellationLogSerializer(serializers.ModelSerializer):
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
