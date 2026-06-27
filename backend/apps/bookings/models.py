from django.db import models
from django.conf import settings
import uuid
import os


def booking_document_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1]
    return f'bookings/{instance.booking.id}/documents/{uuid.uuid4()}.{ext}'


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    TYPE_CHOICES = [
        ('consultation', 'Initial Consultation'),
        ('followup', 'Follow-up Session'),
        ('document_review', 'Document Review'),
        ('representation', 'Legal Representation'),
    ]
    REFUND_STATUS_CHOICES = [
        ('none', 'بدون بازگشت وجه'),
        ('requested', 'درخواست بازگشت وجه'),
        ('not_eligible', 'غیرقابل بازگشت'),
        ('approved', 'تایید شده'),
        ('paid', 'پرداخت شده'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        limit_choices_to={'role': 'customer'},
    )
    lawyer = models.ForeignKey(
        'lawyers.LawyerProfile',
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    booking_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='consultation')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    subject = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    practice_area = models.CharField(max_length=50, blank=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_bookings',
    )
    cancellation_reason = models.TextField(blank=True)
    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='none')
    refund_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    cancellation_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    refund_note = models.TextField(blank=True)

    # Lawyer notes (private)
    lawyer_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    # Meeting details
    meeting_link = models.URLField(blank=True)
    meeting_location = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        ordering = ['-scheduled_at']

    def __str__(self):
        return f'{self.customer.full_name} → {self.lawyer.user.full_name} @ {self.scheduled_at:%Y-%m-%d %H:%M}'


class BookingDocument(models.Model):
    DOCUMENT_TYPES = [
        ('id', 'Government ID'),
        ('contract', 'Contract'),
        ('evidence', 'Evidence'),
        ('court_filing', 'Court Filing'),
        ('financial', 'Financial Record'),
        ('medical', 'Medical Record'),
        ('property', 'Property Document'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to=booking_document_path)
    file_size = models.PositiveIntegerField(default=0)   # bytes
    mime_type = models.CharField(max_length=100, blank=True)
    is_confidential = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.title} ({self.get_document_type_display()})'

    @property
    def file_url(self):
        return self.file.url if self.file else None

    @property
    def file_size_kb(self):
        return round(self.file_size / 1024, 1)


class BookingCancellationLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='cancellation_logs')
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    hours_before_session = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    cancellation_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    refund_status = models.CharField(max_length=20, default='none')
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_cancellation_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'Cancellation {self.booking_id} - {self.refund_status}'
