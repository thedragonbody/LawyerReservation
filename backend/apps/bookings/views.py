from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Booking, BookingDocument, BookingCancellationLog
from .serializers import (
    BookingSerializer, CreateBookingSerializer,
    LawyerBookingUpdateSerializer, UploadDocumentSerializer,
    BookingDocumentSerializer,
)
from apps.lawyers.permissions import IsLawyer, IsCustomer



def _booking_invoice_payload(booking, request=None):
    """Build a simple invoice payload after a confirmed booking."""
    amount = getattr(booking.lawyer, 'consultation_fee', 0) or 0
    scheduled = timezone.localtime(booking.scheduled_at) if booking.scheduled_at else None
    return {
        'invoice_number': str(booking.id).split('-')[0].upper(),
        'booking_code': str(booking.id).split('-')[0].upper(),
        'booking_id': str(booking.id),
        'customer_name': booking.customer.full_name,
        'customer_phone': booking.customer.phone,
        'lawyer_name': booking.lawyer.user.full_name,
        'lawyer_first_name': booking.lawyer.user.first_name,
        'lawyer_last_name': booking.lawyer.user.last_name,
        'scheduled_at': scheduled.isoformat() if scheduled else None,
        'date': scheduled.date().isoformat() if scheduled else None,
        'time': scheduled.strftime('%H:%M') if scheduled else None,
        'duration_minutes': booking.duration_minutes,
        'subject': booking.subject,
        'description': booking.description,
        'upload_notice': 'شما می‌توانید مدارک مورد نیاز رزرو مشاوره خود را در حساب کاربری خود بارگذاری نمایید.',
        'session_type': 'phone' if 'تلفنی' in (booking.description or booking.subject or '') else 'in_person',
        'session_type_display': 'تلفنی' if 'تلفنی' in (booking.description or booking.subject or '') else 'حضوری',
        'office_address': booking.lawyer.office_address if 'تلفنی' not in (booking.description or booking.subject or '') else '',
        'practice_area': booking.practice_area,
        'amount': str(amount),
        'currency': 'IRR',
        'status': booking.status,
    }


def _send_booking_sms(booking):
    """Send/print booking confirmation SMS to customer and lawyer.

    Replace the print block with your SMS provider call in production.
    """
    code = str(booking.id).split('-')[0].upper()
    lawyer_user = booking.lawyer.user
    customer_user = booking.customer
    lawyer_display = f"{lawyer_user.first_name} {lawyer_user.last_name}".strip() or lawyer_user.full_name
    customer_display = customer_user.full_name
    local_scheduled = timezone.localtime(booking.scheduled_at)
    date_text = local_scheduled.strftime('%Y-%m-%d')
    time_text = local_scheduled.strftime('%H:%M')
    session_type = 'تلفنی' if 'تلفنی' in (booking.description or booking.subject or '') else 'حضوری'

    customer_message = (
        f"کاربر گرامی رزرو وقت {session_type} شما با جناب آقای {lawyer_display} "
        f"در تاریخ {date_text} ساعت {time_text} به کد {code} ثبت شد"
    )
    lawyer_message = (
        f"وکیل گرامی، وقت {session_type} شما با {customer_display} "
        f"در تاریخ {date_text} ساعت {time_text} به کد {code} رزرو شد"
    )

    # Development fallback: print SMS in backend terminal.
    print("=" * 60)
    print(f"LEXARA BOOKING SMS -> CUSTOMER {customer_user.phone}")
    print(customer_message)
    print(f"LEXARA BOOKING SMS -> LAWYER {lawyer_user.phone}")
    print(lawyer_message)
    print("=" * 60)

    return {
        'customer': {'phone': customer_user.phone, 'message': customer_message, 'sent': True},
        'lawyer': {'phone': lawyer_user.phone, 'message': lawyer_message, 'sent': True},
    }

# ─── Customer Views ────────────────────────────────────────────────────────────



def _booking_amount(booking):
    try:
        return int(getattr(booking.lawyer, 'consultation_fee', 0) or 0)
    except Exception:
        return 0


def _calculate_cancel_refund(booking):
    amount = _booking_amount(booking)
    now = timezone.now()
    scheduled = booking.scheduled_at
    hours_before = 0
    if scheduled:
        hours_before = max((scheduled - now).total_seconds() / 3600, 0)

    if hours_before >= 24:
        fee = round(amount * 0.09)
        refund = max(amount - fee, 0)
        refund_status = 'requested'
        message = 'لغو قبل از ۲۴ ساعت انجام شد؛ مبلغ قابل بازگشت با کسر ۹٪ کارمزد ثبت شد.'
    else:
        fee = amount
        refund = 0
        refund_status = 'not_eligible'
        message = 'لغو کمتر از ۲۴ ساعت مانده به جلسه انجام شد؛ طبق قوانین مبلغ قابل بازگشت نیست.'

    return {
        'amount': amount,
        'hours_before': round(hours_before, 2),
        'refund_amount': refund,
        'cancellation_fee': fee,
        'refund_status': refund_status,
        'message': message,
    }


def _send_cancel_sms_stub(booking, payload):
    try:
        print(f"LEXARA CANCEL SMS -> CUSTOMER {booking.customer.phone}: {payload['message']}")
        print(f"LEXARA CANCEL SMS -> LAWYER {booking.lawyer.user.phone}: رزرو {booking.subject} لغو شد.")
    except Exception:
        pass

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def customer_bookings(request):
    if request.method == 'GET':
        if request.user.role != 'customer':
            return Response({'detail': 'Only customers can view their bookings.'}, status=403)
        bookings = Booking.objects.filter(customer=request.user).select_related('lawyer__user').prefetch_related('documents')
        ser = BookingSerializer(bookings, many=True, context={'request': request})
        return Response(ser.data)

    # POST — create booking (customer only)
    if request.user.role != 'customer':
        return Response({'detail': 'Only customers can create bookings.'}, status=403)

    ser = CreateBookingSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    booking = ser.save(customer=request.user, status='confirmed')

    # Update lawyer booking count
    lawyer = booking.lawyer
    lawyer.total_bookings += 1
    lawyer.save(update_fields=['total_bookings'])

    booking_data = BookingSerializer(booking, context={'request': request}).data
    invoice = _booking_invoice_payload(booking, request=request)
    sms = _send_booking_sms(booking)
    booking_data['invoice'] = invoice
    booking_data['upload_notice'] = invoice.get('upload_notice')
    booking_data['sms'] = sms

    return Response(booking_data, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Access control
    is_customer = request.user == booking.customer
    is_lawyer = (request.user.role == 'lawyer' and
                 hasattr(request.user, 'lawyer_profile') and
                 request.user.lawyer_profile == booking.lawyer)

    if not (is_customer or is_lawyer):
        return Response({'detail': 'Not authorized.'}, status=403)

    if request.method == 'GET':
        ser = BookingSerializer(booking, context={'request': request})
        # Include lawyer_notes only for lawyers
        data = ser.data
        if is_customer:
            data.pop('lawyer_notes', None)
        return Response(data)

    if request.method == 'PATCH':
        if is_lawyer:
            ser = LawyerBookingUpdateSerializer(booking, data=request.data, partial=True)
        elif is_customer and request.data.get('status') == 'cancelled':
            if booking.status not in ('pending', 'confirmed'):
                return Response({'detail': 'Cannot cancel this booking.'}, status=400)
            booking.status = 'cancelled'
            booking.save(update_fields=['status'])
            return Response(BookingSerializer(booking, context={'request': request}).data)
        else:
            return Response({'detail': 'Customers can only cancel bookings.'}, status=403)

        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(BookingSerializer(booking, context={'request': request}).data)

    if request.method == 'DELETE':
        if not is_customer:
            return Response({'detail': 'Only customers can delete bookings.'}, status=403)
        if booking.status not in ('pending',):
            return Response({'detail': 'Only pending bookings can be deleted.'}, status=400)
        booking.delete()
        return Response(status=204)


# ─── Document Upload ──────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def booking_documents(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    is_customer = request.user == booking.customer
    is_lawyer = (request.user.role == 'lawyer' and
                 hasattr(request.user, 'lawyer_profile') and
                 request.user.lawyer_profile == booking.lawyer)

    if not (is_customer or is_lawyer):
        return Response({'detail': 'Not authorized.'}, status=403)

    if request.method == 'GET':
        docs = booking.documents.all()
        ser = BookingDocumentSerializer(docs, many=True, context={'request': request})
        return Response(ser.data)

    # POST — upload document
    if not is_customer:
        return Response({'detail': 'Only customers upload documents.'}, status=403)

    ser = UploadDocumentSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    file = ser.validated_data['file']
    doc = BookingDocument.objects.create(
        booking=booking,
        uploaded_by=request.user,
        document_type=ser.validated_data['document_type'],
        title=ser.validated_data['title'],
        file=file,
        file_size=file.size,
        mime_type=file.content_type,
        is_confidential=ser.validated_data['is_confidential'],
    )
    return Response(BookingDocumentSerializer(doc, context={'request': request}).data, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_document(request, booking_id, doc_id):
    booking = get_object_or_404(Booking, id=booking_id)
    doc = get_object_or_404(BookingDocument, id=doc_id, booking=booking)

    if request.user != doc.uploaded_by:
        return Response({'detail': 'Not authorized.'}, status=403)

    doc.file.delete(save=False)
    doc.delete()
    return Response(status=204)


# ─── Lawyer Bookings View ─────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsLawyer])
def lawyer_bookings(request):
    try:
        profile = request.user.lawyer_profile
    except Exception:
        return Response({'detail': 'Lawyer profile not found.'}, status=404)

    status_filter = request.query_params.get('status')
    qs = Booking.objects.filter(lawyer=profile).select_related('customer').prefetch_related('documents').order_by('scheduled_at', 'created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)

    ser = BookingSerializer(qs, many=True, context={'request': request})
    return Response(ser.data)


# ─── Available Slots ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_slots(request, lawyer_id):
    """Return available time slots for a lawyer on a given date.

    Exact date availability has priority over weekly availability.
    Closed days are returned with is_closed=True so the frontend can show them red.
    Booked slots are returned with available=False so the frontend can show them red/disabled.
    """
    from apps.lawyers.models import LawyerProfile, Availability
    from datetime import datetime, timedelta

    date_str = request.query_params.get('date')
    if not date_str:
        return Response({'detail': 'date param required (YYYY-MM-DD).'}, status=400)

    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'detail': 'Invalid date format.'}, status=400)

    try:
        lawyer = LawyerProfile.objects.get(id=lawyer_id, verification_status='verified')
    except LawyerProfile.DoesNotExist:
        return Response({'detail': 'وکیل پیدا نشد.'}, status=404)

    if lawyer.verification_status != 'verified':
        return Response({'detail': 'این وکیل هنوز توسط ادمین تایید نشده است.'}, status=403)

    exact_avails = list(Availability.objects.filter(lawyer=lawyer, date=query_date).order_by('start_time'))

    if exact_avails:
        if any(getattr(a, 'is_closed', False) for a in exact_avails):
            return Response({
                'slots': [],
                'date': date_str,
                'is_closed': True,
                'has_availability': False,
                'message': 'متاسفانه این روز تعطیل میباشد',
            })
        avails = [a for a in exact_avails if not getattr(a, 'is_closed', False)]
    else:
        day_abbr = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][query_date.weekday()]
        avails = list(
            Availability.objects
            .filter(lawyer=lawyer, day_of_week=day_abbr, is_closed=False)
            .order_by('start_time')
        )

    if not avails:
        return Response({
            'slots': [],
            'date': date_str,
            'is_closed': False,
            'has_availability': False,
            'message': 'برای این روز ساعت فعالی ثبت نشده است.',
        })

    booked_times = list(
        Booking.objects.filter(
            lawyer=lawyer,
            scheduled_at__date=query_date,
            status__in=['pending', 'confirmed'],
        ).values_list('scheduled_at', flat=True)
    )

    slots = []
    for avail in avails:
        current = datetime.combine(query_date, avail.start_time)
        end_time = datetime.combine(query_date, avail.end_time)
        duration_minutes = getattr(avail, 'slot_duration_minutes', 60) or 60
        duration = timedelta(minutes=duration_minutes)

        while current + duration <= end_time:
            is_booked = any(
                abs((bt.replace(tzinfo=None) - current).total_seconds()) < 60
                for bt in booked_times
            )
            slots.append({
                'time': current.strftime('%H:%M'),
                'datetime': current.isoformat(),
                'available': not is_booked,
                'is_booked': is_booked,
                'duration_minutes': duration_minutes,
            })
            current += duration

    return Response({
        'slots': slots,
        'date': date_str,
        'is_closed': False,
        'has_availability': True,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related('customer', 'lawyer__user'), id=booking_id)

    is_customer = booking.customer_id == request.user.id
    is_lawyer = hasattr(request.user, 'lawyer_profile') and booking.lawyer_id == getattr(request.user.lawyer_profile, 'id', None)
    is_admin = bool(request.user.is_staff or request.user.is_superuser)

    if not (is_customer or is_lawyer or is_admin):
        return Response({'detail': 'اجازه لغو این رزرو را ندارید.'}, status=403)

    if booking.status in ['cancelled', 'completed', 'rejected']:
        return Response({'detail': 'این رزرو دیگر قابل لغو نیست.'}, status=400)

    reason = str(request.data.get('reason') or '').strip()
    payload = _calculate_cancel_refund(booking)

    booking.status = 'cancelled'
    booking.cancelled_at = timezone.now()
    booking.cancelled_by = request.user
    booking.cancellation_reason = reason
    booking.refund_status = payload['refund_status']
    booking.refund_amount = payload['refund_amount']
    booking.cancellation_fee = payload['cancellation_fee']
    booking.refund_note = payload['message']
    booking.save(update_fields=[
        'status', 'cancelled_at', 'cancelled_by', 'cancellation_reason',
        'refund_status', 'refund_amount', 'cancellation_fee', 'refund_note', 'updated_at'
    ])

    log = BookingCancellationLog.objects.create(
        booking=booking,
        cancelled_by=request.user,
        reason=reason,
        hours_before_session=payload['hours_before'],
        refund_amount=payload['refund_amount'],
        cancellation_fee=payload['cancellation_fee'],
        refund_status=payload['refund_status'],
    )

    _send_cancel_sms_stub(booking, payload)

    return Response({
        'detail': 'رزرو لغو شد.',
        'message': payload['message'],
        'booking_id': str(booking.id),
        'status': booking.status,
        'refund_status': booking.refund_status,
        'refund_amount': int(booking.refund_amount),
        'cancellation_fee': int(booking.cancellation_fee),
        'hours_before_session': payload['hours_before'],
        'log_id': str(log.id),
    })
