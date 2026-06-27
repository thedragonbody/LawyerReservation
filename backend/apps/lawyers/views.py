import json
import requests
from django.conf import settings
from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.db import models

from .models import LawyerProfile, Review
from .serializers import (
    LawyerListSerializer, LawyerDetailSerializer,
    LawyerProfileUpdateSerializer, CreateReviewSerializer, AvailabilitySerializer,
)
from .filters import LawyerFilter
from .permissions import IsLawyer


class LawyerListView(generics.ListAPIView):
    serializer_class = LawyerListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LawyerFilter
    search_fields = ['user__first_name', 'user__last_name', 'headline', 'bio', 'bar_number', 'practice_areas__area']
    ordering_fields = ['average_rating', 'years_experience', 'hourly_rate', 'total_bookings']
    ordering = ['-is_featured', '-average_rating']

    def get_queryset(self):
        return (
            LawyerProfile.objects
            .filter(verification_status='verified')
            .select_related('user')
            .prefetch_related('practice_areas', 'availability')
            .distinct()
        )


class LawyerDetailView(generics.RetrieveAPIView):
    serializer_class = LawyerDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        return (
            LawyerProfile.objects
            .filter(verification_status='verified')
            .select_related('user')
            .prefetch_related('practice_areas', 'education', 'availability', 'reviews__customer')
            .distinct()
        )


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsLawyer])
def my_profile(request):
    """Lawyer manages their own profile."""
    try:
        profile = LawyerProfile.objects.get(user=request.user)
    except LawyerProfile.DoesNotExist:
        if request.method == 'GET':
            return Response({'detail': 'Profile not set up yet.'}, status=404)
        # Auto-create on first update
        profile = LawyerProfile.objects.create(user=request.user, bar_number=f'PENDING-{request.user.id}')

    if request.method == 'GET':
        ser = LawyerDetailSerializer(profile, context={'request': request})
        return Response(ser.data)

    data = request.data.copy()
    manual_office_address = request.data.get('office_address', None)

    avatar = request.FILES.get('avatar')
    # avatar belongs to User, not LawyerProfile, so remove it before serializer validation.
    if hasattr(data, 'pop'):
        data.pop('avatar', None)
    if avatar:
        request.user.avatar = avatar
        request.user.save(update_fields=['avatar'])

    # Multiple specialties can be submitted as repeated `areas`, repeated `specialties`, comma text, or a primary_area.
    areas = []
    if hasattr(data, 'getlist'):
        areas = data.getlist('areas') or data.getlist('specialties')
    raw_primary = data.pop('primary_area', None) or data.pop('specialization', None)
    if isinstance(raw_primary, list):
        raw_primary = raw_primary[0] if raw_primary else None
    raw_areas = data.pop('areas', None) or data.pop('specialties', None)
    if raw_areas and not areas:
        if isinstance(raw_areas, list):
            areas = raw_areas
        else:
            areas = [x.strip() for x in str(raw_areas).split(',') if x.strip()]
    if raw_primary and raw_primary not in areas:
        areas.insert(0, raw_primary)

    ser = LawyerProfileUpdateSerializer(profile, data=data, partial=True)
    ser.is_valid(raise_exception=True)
    updated = ser.save()
    if manual_office_address is not None:
        updated.office_address = str(manual_office_address)
        updated.save(update_fields=['office_address'])

    if areas:
        from .models import PracticeArea
        updated.practice_areas.all().delete()
        for index, area in enumerate(areas):
            PracticeArea.objects.create(lawyer=updated, area=area, is_primary=(index == 0))

    return Response(LawyerDetailSerializer(updated, context={'request': request}).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_review(request, lawyer_id):
    """Customers can review a lawyer after a completed booking."""
    if request.user.role != 'customer':
        return Response({'detail': 'فقط موکل می‌تواند امتیاز ثبت کند.'}, status=403)

    try:
        lawyer = LawyerProfile.objects.exclude(verification_status='rejected').get(id=lawyer_id)
    except LawyerProfile.DoesNotExist:
        return Response({'detail': 'وکیل پیدا نشد.'}, status=404)

    if lawyer.verification_status != 'verified':
        return Response({'detail': 'این وکیل هنوز توسط ادمین تایید نشده است.'}, status=403)

    # Check if customer has a completed booking with this lawyer
    from apps.bookings.models import Booking
    has_booking = Booking.objects.filter(
        customer=request.user,
        lawyer=lawyer,
        status='completed',
    ).exists()
    if not has_booking:
        return Response({'detail': 'فقط بعد از انجام مشاوره می‌توانید امتیاز ثبت کنید.'}, status=403)

    existing = Review.objects.filter(lawyer=lawyer, customer=request.user).first()

    ser = CreateReviewSerializer(existing, data=request.data, partial=bool(existing))
    ser.is_valid(raise_exception=True)
    review = ser.save(lawyer=lawyer, customer=request.user)

    # Update lawyer stats
    reviews = Review.objects.filter(lawyer=lawyer)
    lawyer.total_reviews = reviews.count()
    lawyer.average_rating = reviews.aggregate(avg=models.Avg('rating'))['avg'] or 0
    lawyer.save(update_fields=['total_reviews', 'average_rating'])

    status_code = 200 if existing else 201
    return Response(CreateReviewSerializer(review).data, status=status_code)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsLawyer])
def lawyer_dashboard_stats(request):
    """Stats for lawyer's private dashboard."""
    from apps.bookings.models import Booking
    from django.utils import timezone
    from django.db.models import Count
    from datetime import timedelta

    try:
        profile = LawyerProfile.objects.get(user=request.user)
    except LawyerProfile.DoesNotExist:
        return Response({'detail': 'Profile not found.'}, status=404)

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    bookings = Booking.objects.filter(lawyer=profile)

    upcoming = bookings.filter(status='confirmed', scheduled_at__gte=now).order_by('scheduled_at')[:5]
    from apps.bookings.serializers import BookingSerializer

    month_bookings = bookings.filter(created_at__gte=month_start)
    completed_or_confirmed = month_bookings.filter(status__in=['confirmed', 'completed'])
    fee = int(profile.consultation_fee or 0)
    hot_hours_qs = (
        bookings.exclude(scheduled_at=None)
        .values('scheduled_at__hour')
        .annotate(count=Count('id'))
        .order_by('-count')[:3]
    )
    hot_hours = [
        {'hour': f"{int(x['scheduled_at__hour'] or 0):02d}:00", 'count': x['count']}
        for x in hot_hours_qs
    ]

    return Response({
        'total_bookings': bookings.count(),
        'pending_bookings': bookings.filter(status='pending').count(),
        'confirmed_bookings': bookings.filter(status='confirmed').count(),
        'completed_bookings': bookings.filter(status='completed').count(),
        'cancelled_bookings': bookings.filter(status='cancelled').count(),
        'monthly_bookings': month_bookings.count(),
        'estimated_revenue': completed_or_confirmed.count() * fee,
        'hot_hours': hot_hours,
        'average_rating': float(profile.average_rating),
        'total_reviews': profile.total_reviews,
        'is_accepting_clients': profile.is_accepting_clients,
        'upcoming_bookings': BookingSerializer(upcoming, many=True, context={'request': request}).data,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsLawyer])
def availability_day(request):
    """Get/save exact working hours for one calendar date."""
    from datetime import datetime
    from .models import Availability

    try:
        profile = LawyerProfile.objects.get(user=request.user)
    except LawyerProfile.DoesNotExist:
        return Response({'detail': 'Profile not found.'}, status=404)

    date_str = request.query_params.get('date') or request.data.get('date')
    if not date_str:
        return Response({'detail': 'date is required.'}, status=400)

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'detail': 'date format must be YYYY-MM-DD.'}, status=400)

    if request.method == 'GET':
        items = Availability.objects.filter(lawyer=profile, date=target_date).order_by('start_time')
        return Response(AvailabilitySerializer(items, many=True, context={'request': request}).data)

    is_closed = str(request.data.get('is_closed', 'false')).lower() in ['1', 'true', 'yes', 'on']
    Availability.objects.filter(lawyer=profile, date=target_date).delete()

    if is_closed:
        item = Availability.objects.create(
            lawyer=profile,
            date=target_date,
            day_of_week=None,
            start_time='00:00',
            end_time='00:00',
            is_closed=True,
            slot_duration_minutes=30,
        )
        return Response(AvailabilitySerializer([item], many=True, context={'request': request}).data)

    slots = request.data.get('slots', [])
    if isinstance(slots, str):
        import json
        try:
            slots = json.loads(slots)
        except Exception:
            slots = []

    created = []
    for slot in slots:
        start = slot.get('start_time') or slot.get('start')
        end = slot.get('end_time') or slot.get('end')
        if start and end:
            created.append(Availability.objects.create(
                lawyer=profile,
                date=target_date,
                day_of_week=None,
                start_time=start,
                end_time=end,
                is_closed=False,
                slot_duration_minutes=30,
            ))
    return Response(AvailabilitySerializer(created, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([])
def justive_analyze(request):
    """
    Justive AI analyzer:
    - Uses OpenAI if OPENAI_API_KEY exists.
    - Falls back to local deterministic analyzer.
    - Does not store user message in database.
    """
    text = str(request.data.get('message') or '').strip()
    if not text:
        return Response({'detail': 'message الزامی است.'}, status=400)

    areas = {
        'family': ['خانواده', 'طلاق', 'مهریه', 'حضانت', 'نفقه'],
        'real_estate': ['ملک', 'املاک', 'سند', 'مبایعه', 'اجاره'],
        'criminal': ['کیفری', 'شکایت', 'جرم', 'کلاهبرداری', 'سرقت'],
        'employment': ['کار', 'استخدام', 'بیمه', 'حقوق معوقه', 'کارگر'],
        'tax_law': ['مالیات', 'دارایی', 'اظهارنامه'],
        'immigration': ['مهاجرت', 'ویزا', 'اقامت'],
    }
    cities = ['تهران', 'مشهد', 'اصفهان', 'شیراز', 'تبریز', 'کرج', 'قم', 'اهواز', 'رشت', 'یزد']

    def local_result():
        area = ''
        for k, words in areas.items():
            if any(w in text for w in words):
                area = k
                break
        city = next((c for c in cities if c in text), '')
        max_fee = ''
        if '۳۰۰' in text or '300' in text:
            max_fee = '300000'
        elif '۵۰۰' in text or '500' in text:
            max_fee = '500000'
        elif '۸۰۰' in text or '800' in text:
            max_fee = '800000'
        elif 'میلیون' in text or '1200' in text or '۱.۲' in text:
            max_fee = '1200000'

        answer = 'موضوع، شهر، بودجه و نوع مشاوره را بنویس تا وکیل مناسب‌تر را پیشنهاد بدهم.'
        if area == 'family':
            answer = 'برای طلاق، مهریه، حضانت یا نفقه، وکیل خانواده مناسب‌تر است.'
        elif area == 'real_estate':
            answer = 'برای سند، مبایعه‌نامه، اجاره یا اختلاف ملکی، وکیل ملک و املاک مناسب‌تر است.'
        elif area == 'criminal':
            answer = 'برای شکایت، جرم، کلاهبرداری یا پرونده کیفری، وکیل کیفری و جزایی مناسب‌تر است.'
        elif area == 'employment':
            answer = 'برای اختلاف کار، بیمه یا حقوق معوقه، وکیل حقوق کار مناسب‌تر است.'
        elif area == 'tax_law':
            answer = 'برای مالیات و دارایی، وکیل مالیاتی مناسب‌تر است.'
        elif area == 'immigration':
            answer = 'برای ویزا، اقامت و پرونده مهاجرتی، وکیل مهاجرت مناسب‌تر است.'
        return {'answer': answer, 'area': area, 'city': city, 'max_fee': max_fee}

    result = local_result()
    ai_source = 'fallback'
    openai_enabled = False
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
    if api_key:
        openai_enabled = True
        try:
            prompt = (
                'You are Justive, a Persian legal intake assistant for a lawyer booking app. '
                'Return ONLY JSON with keys: answer, area, city, max_fee. '
                'Allowed area values: family, real_estate, criminal, employment, tax_law, immigration, corporate, civil_litigation, personal_injury, estate_planning, bankruptcy, healthcare_law, environmental_law, international_law, empty string. '
                'Never provide legal verdicts. Do not repeat sensitive details. '
                'User text: ' + text[:1200]
            )
            r = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={
                    'model': getattr(settings, 'JUSTIVE_OPENAI_MODEL', 'gpt-4o-mini'),
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.2,
                },
                timeout=12,
            )
            if r.ok:
                content = r.json()['choices'][0]['message']['content'].strip().strip('`')
                if content.startswith('json'):
                    content = content[4:].strip()
                parsed = json.loads(content)
                result.update({
                    'answer': str(parsed.get('answer') or result.get('answer') or ''),
                    'area': str(parsed.get('area') or result.get('area') or ''),
                    'city': str(parsed.get('city') or result.get('city') or ''),
                    'max_fee': str(parsed.get('max_fee') or result.get('max_fee') or ''),
                })
                ai_source = 'openai'
        except Exception:
            pass

    lawyers = LawyerProfile.objects.filter(verification_status='verified', is_accepting_clients=True)
    if result.get('area'):
        lawyers = lawyers.filter(practice_areas__area=result['area']).distinct()
    if result.get('city'):
        lawyers = lawyers.filter(city__icontains=result['city'])
    if result.get('max_fee'):
        try:
            lawyers = lawyers.filter(consultation_fee__lte=int(result['max_fee']))
        except Exception:
            pass

    suggested = []
    for l in lawyers.select_related('user').order_by('-average_rating', '-total_bookings')[:5]:
        suggested.append({
            'id': str(l.id),
            'name': l.user.full_name,
            'city': l.city,
            'fee': int(l.consultation_fee or 0),
            'rating': float(l.average_rating or 0),
        })

    return Response({
        'answer': result.get('answer') or 'پیشنهاد اولیه آماده شد.',
        'area': result.get('area') or '',
        'city': result.get('city') or '',
        'max_fee': result.get('max_fee') or '',
        'suggested_lawyers': suggested,
        'ai_source': ai_source,
        'openai_enabled': openai_enabled,
        'privacy': 'متن گفتگو در دیتابیس ذخیره نمی‌شود؛ پاک‌سازی یک‌روزه سمت کاربر فعال است.',
    })
