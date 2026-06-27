from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404

from apps.accounts.models import User
from apps.lawyers.models import LawyerProfile, Review
from apps.bookings.models import Booking, BookingDocument, BookingCancellationLog
from .models import CommissionSetting, DiscountCode, LawyerSettlement, SiteContent
from .serializers import (
    AdminUserSerializer,
    AdminLawyerSerializer,
    AdminBookingSerializer,
    AdminBookingDocumentSerializer,
    AdminReviewSerializer,
    AdminCancellationLogSerializer, CommissionSettingSerializer, DiscountCodeSerializer,
    LawyerSettlementSerializer, SiteContentSerializer,
)


def _paginate(request, qs, serializer_class):
    try:
        page = max(int(request.query_params.get('page', 1)), 1)
    except Exception:
        page = 1
    try:
        page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 100)
    except Exception:
        page_size = 20

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    ser = serializer_class(qs[start:end], many=True, context={'request': request})
    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': ser.data,
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def overview(request):
    now = timezone.now()
    bookings = Booking.objects.all()
    lawyers = LawyerProfile.objects.all()
    users = User.objects.all()

    amount_sum = 0
    for booking in bookings.filter(status__in=['confirmed', 'completed']).select_related('lawyer'):
        try:
            amount_sum += int(booking.lawyer.consultation_fee or 0)
        except Exception:
            pass

    return Response({
        'users_total': users.count(),
        'customers_total': users.filter(role='customer').count(),
        'lawyers_total': lawyers.count(),
        'lawyers_pending': lawyers.filter(verification_status='pending').count(),
        'lawyers_verified': lawyers.filter(verification_status='verified').count(),
        'lawyers_rejected': lawyers.filter(verification_status='rejected').count(),
        'bookings_total': bookings.count(),
        'bookings_pending': bookings.filter(status='pending').count(),
        'bookings_confirmed': bookings.filter(status='confirmed').count(),
        'bookings_completed': bookings.filter(status='completed').count(),
        'bookings_cancelled': bookings.filter(status='cancelled').count(),
        'documents_total': BookingDocument.objects.count(),
        'estimated_revenue': amount_sum,
        'today_bookings': bookings.filter(scheduled_at__date=now.date()).count(),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def users(request):
    qs = User.objects.all().order_by('-created_at')
    q = request.query_params.get('q', '').strip()
    role = request.query_params.get('role', '').strip()
    active = request.query_params.get('is_active', '').strip()

    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q))
    if role in ('customer', 'lawyer'):
        qs = qs.filter(role=role)
    if active in ('true', 'false'):
        qs = qs.filter(is_active=(active == 'true'))

    return _paginate(request, qs, AdminUserSerializer)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def lawyers(request):
    qs = LawyerProfile.objects.select_related('user').prefetch_related('practice_areas').order_by('-created_at')
    q = request.query_params.get('q', '').strip()
    status = request.query_params.get('status', '').strip()
    city = request.query_params.get('city', '').strip()

    if q:
        qs = qs.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__phone__icontains=q) |
            Q(bar_number__icontains=q) |
            Q(headline__icontains=q)
        )
    if status in ('pending', 'verified', 'rejected'):
        qs = qs.filter(verification_status=status)
    if city:
        qs = qs.filter(Q(city__icontains=city) | Q(office_address__icontains=city))

    return _paginate(request, qs, AdminLawyerSerializer)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdminUser])
def lawyer_detail(request, lawyer_id):
    try:
        lawyer = LawyerProfile.objects.select_related('user').prefetch_related('practice_areas').get(id=lawyer_id)
    except LawyerProfile.DoesNotExist:
        return Response({'detail': 'وکیل پیدا نشد.'}, status=404)

    if request.method == 'GET':
        return Response(AdminLawyerSerializer(lawyer, context={'request': request}).data)

    allowed = {
        'verification_status', 'is_featured', 'is_accepting_clients',
        'headline', 'bio', 'city', 'office_address', 'consultation_fee', 'years_experience', 'bar_number',
    }
    for field in allowed:
        if field in request.data:
            setattr(lawyer, field, request.data.get(field))

    if lawyer.verification_status not in ('pending', 'verified', 'rejected'):
        return Response({'detail': 'وضعیت تایید نامعتبر است.'}, status=400)

    lawyer.save()
    return Response(AdminLawyerSerializer(lawyer, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def verify_lawyer(request, lawyer_id):
    try:
        lawyer = LawyerProfile.objects.get(id=lawyer_id)
    except LawyerProfile.DoesNotExist:
        return Response({'detail': 'وکیل پیدا نشد.'}, status=404)

    status_value = request.data.get('status', 'verified')
    if status_value not in ('verified', 'rejected', 'pending'):
        return Response({'detail': 'status باید verified یا rejected یا pending باشد.'}, status=400)

    lawyer.verification_status = status_value
    lawyer.save(update_fields=['verification_status', 'updated_at'])
    return Response(AdminLawyerSerializer(lawyer, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def bookings(request):
    qs = Booking.objects.select_related('customer', 'lawyer__user').prefetch_related('documents').order_by('-created_at')
    q = request.query_params.get('q', '').strip()
    status = request.query_params.get('status', '').strip()

    if q:
        qs = qs.filter(
            Q(customer__first_name__icontains=q) |
            Q(customer__last_name__icontains=q) |
            Q(customer__phone__icontains=q) |
            Q(lawyer__user__first_name__icontains=q) |
            Q(lawyer__user__last_name__icontains=q) |
            Q(lawyer__user__phone__icontains=q) |
            Q(subject__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    return _paginate(request, qs, AdminBookingSerializer)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def booking_update(request, booking_id):
    try:
        booking = Booking.objects.select_related('customer', 'lawyer__user').get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({'detail': 'رزرو پیدا نشد.'}, status=404)

    allowed_status = ['pending', 'confirmed', 'completed', 'cancelled', 'rejected']
    if 'status' in request.data:
        if request.data.get('status') not in allowed_status:
            return Response({'detail': 'وضعیت رزرو نامعتبر است.'}, status=400)
        booking.status = request.data.get('status')
    for field in ['meeting_link', 'meeting_location', 'rejection_reason']:
        if field in request.data:
            setattr(booking, field, request.data.get(field))
    booking.save()
    return Response(AdminBookingSerializer(booking, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def documents(request):
    qs = BookingDocument.objects.select_related('booking', 'uploaded_by').order_by('-uploaded_at')
    q = request.query_params.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(uploaded_by__first_name__icontains=q) | Q(uploaded_by__last_name__icontains=q))
    return _paginate(request, qs, AdminBookingDocumentSerializer)



@api_view(['GET', 'PATCH'])
@permission_classes([IsAdminUser])
def user_detail(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'detail': 'کاربر پیدا نشد.'}, status=404)

    if request.method == 'GET':
        return Response(AdminUserSerializer(user, context={'request': request}).data)

    for field in ['first_name', 'last_name', 'is_active']:
        if field in request.data:
            setattr(user, field, request.data.get(field))
    user.save()
    return Response(AdminUserSerializer(user, context={'request': request}).data)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAdminUser])
def review_detail(request, review_id):
    try:
        review = Review.objects.select_related('lawyer__user', 'customer').get(id=review_id)
    except Review.DoesNotExist:
        return Response({'detail': 'نظر پیدا نشد.'}, status=404)

    if request.method == 'GET':
        return Response(AdminReviewSerializer(review, context={'request': request}).data)

    if request.method == 'DELETE':
        lawyer = review.lawyer
        review.delete()
        reviews = lawyer.reviews.all()
        lawyer.total_reviews = reviews.count()
        lawyer.average_rating = (sum([r.rating for r in reviews]) / reviews.count()) if reviews.count() else 0
        lawyer.save(update_fields=['total_reviews', 'average_rating'])
        return Response(status=204)

    for field in ['rating', 'comment', 'is_anonymous']:
        if field in request.data:
            setattr(review, field, request.data.get(field))
    review.save()

    lawyer = review.lawyer
    reviews_qs = lawyer.reviews.all()
    lawyer.total_reviews = reviews_qs.count()
    lawyer.average_rating = (sum([r.rating for r in reviews_qs]) / reviews_qs.count()) if reviews_qs.count() else 0
    lawyer.save(update_fields=['total_reviews', 'average_rating'])

    return Response(AdminReviewSerializer(review, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def reviews(request):
    qs = Review.objects.select_related('lawyer__user', 'customer').order_by('-created_at')
    q = request.query_params.get('q', '').strip()
    rating = request.query_params.get('rating', '').strip()
    if q:
        qs = qs.filter(
            Q(comment__icontains=q) |
            Q(lawyer__user__first_name__icontains=q) |
            Q(lawyer__user__last_name__icontains=q) |
            Q(customer__first_name__icontains=q) |
            Q(customer__last_name__icontains=q) |
            Q(customer__phone__icontains=q)
        )
    if rating:
        qs = qs.filter(rating=rating)
    return _paginate(request, qs, AdminReviewSerializer)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def revenue(request):
    qs = Booking.objects.select_related('customer', 'lawyer__user').filter(status__in=['confirmed', 'completed']).order_by('-created_at')
    total = 0
    items = []
    for b in qs[:200]:
        amount = int(b.lawyer.consultation_fee or 0)
        total += amount
        items.append({
            'booking_id': str(b.id),
            'lawyer_name': b.lawyer.user.full_name,
            'customer_name': b.customer.full_name,
            'amount': amount,
            'status': b.status,
            'scheduled_at': b.scheduled_at,
            'created_at': b.created_at,
        })
    return Response({
        'estimated_revenue': total,
        'count': qs.count(),
        'results': items,
    })


def _active_commission_percent():
    obj = CommissionSetting.objects.filter(is_active=True).order_by('-updated_at').first()
    if not obj:
        obj = CommissionSetting.objects.create(title='کمیسیون پیش‌فرض', commission_percent=9, is_active=True)
    return float(obj.commission_percent)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def finance_overview(request):
    commission_percent = _active_commission_percent()
    qs = Booking.objects.filter(status__in=['confirmed', 'completed']).select_related('lawyer__user', 'customer')
    gross = 0
    rows = []
    for b in qs:
        amount = int(getattr(b.lawyer, 'consultation_fee', 0) or 0)
        commission = round(amount * commission_percent / 100)
        net = max(amount - commission, 0)
        gross += amount
        rows.append({
            'booking_id': str(b.id),
            'subject': b.subject,
            'lawyer_name': b.lawyer.user.full_name,
            'customer_name': b.customer.full_name,
            'amount': amount,
            'commission_amount': commission,
            'net_amount': net,
            'status': b.status,
            'created_at': b.created_at,
        })
    return Response({
        'commission_percent': commission_percent,
        'gross_revenue': gross,
        'commission_total': round(gross * commission_percent / 100),
        'lawyers_payable': max(gross - round(gross * commission_percent / 100), 0),
        'count': qs.count(),
        'results': rows[:100],
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def commission_settings(request):
    if request.method == 'GET':
        obj = CommissionSetting.objects.filter(is_active=True).order_by('-updated_at').first()
        if not obj:
            obj = CommissionSetting.objects.create(title='کمیسیون پیش‌فرض', commission_percent=9, is_active=True)
        return Response(CommissionSettingSerializer(obj).data)

    obj = CommissionSetting.objects.filter(is_active=True).order_by('-updated_at').first()
    if not obj:
        obj = CommissionSetting(title='کمیسیون پیش‌فرض', is_active=True)
    ser = CommissionSettingSerializer(obj, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save(is_active=True)
    return Response(ser.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def discounts(request):
    if request.method == 'GET':
        return _paginate(request, DiscountCode.objects.all(), DiscountCodeSerializer)
    ser = DiscountCodeSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data, status=201)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAdminUser])
def discount_detail(request, discount_id):
    obj = get_object_or_404(DiscountCode, id=discount_id)
    if request.method == 'DELETE':
        obj.delete()
        return Response({'detail': 'کد تخفیف حذف شد.'})
    ser = DiscountCodeSerializer(obj, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def settlements(request):
    if request.method == 'GET':
        return _paginate(request, LawyerSettlement.objects.select_related('lawyer__user'), LawyerSettlementSerializer)

    lawyer_id = request.data.get('lawyer')
    lawyer = get_object_or_404(LawyerProfile, id=lawyer_id)
    amount = int(request.data.get('amount') or 0)
    commission_percent = _active_commission_percent()
    commission = round(amount * commission_percent / 100)
    settlement = LawyerSettlement.objects.create(
        lawyer=lawyer,
        amount=amount,
        commission_amount=commission,
        net_amount=max(amount - commission, 0),
        status=request.data.get('status') or 'pending',
        note=request.data.get('note') or '',
        created_by=request.user,
    )
    return Response(LawyerSettlementSerializer(settlement).data, status=201)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def settlement_detail(request, settlement_id):
    obj = get_object_or_404(LawyerSettlement, id=settlement_id)
    if request.data.get('status') == 'paid' and obj.status != 'paid':
        obj.paid_at = timezone.now()
    ser = LawyerSettlementSerializer(obj, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def cancellation_logs(request):
    qs = BookingCancellationLog.objects.select_related('booking__customer', 'booking__lawyer__user', 'cancelled_by')
    return _paginate(request, qs, AdminCancellationLogSerializer)


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def site_content(request):
    defaults = [
        ('home_hero', 'صفحه خانه', 'متن اصلی صفحه خانه'),
        ('about', 'درباره ما', 'متن درباره لکسارا'),
        ('contact', 'تماس با ما', 'اطلاعات تماس'),
        ('terms', 'قوانین و مقررات', 'قوانین استفاده از سامانه'),
        ('privacy', 'حریم خصوصی', 'سیاست حریم خصوصی'),
        ('cancel_policy', 'قوانین لغو رزرو', 'لغو قبل از ۲۴ ساعت با کسر ۹٪ و لغو کمتر از ۲۴ ساعت بدون بازگشت وجه.'),
    ]
    for key, title, body in defaults:
        SiteContent.objects.get_or_create(key=key, defaults={'title': title, 'body': body, 'is_active': True})

    if request.method == 'GET':
        return Response(SiteContentSerializer(SiteContent.objects.all(), many=True).data)

    key = request.data.get('key')
    if not key:
        return Response({'detail': 'key الزامی است.'}, status=400)
    obj, _ = SiteContent.objects.get_or_create(key=key)
    ser = SiteContentSerializer(obj, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
