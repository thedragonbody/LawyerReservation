from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.lawyers.permissions import IsCustomer


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCustomer])
def customer_dashboard(request):
    from apps.bookings.models import Booking
    from apps.bookings.serializers import BookingSerializer
    from django.utils import timezone

    bookings = Booking.objects.filter(customer=request.user).select_related('lawyer__user')
    now = timezone.now()

    upcoming = bookings.filter(status='confirmed', scheduled_at__gte=now).order_by('scheduled_at')[:5]

    return Response({
        'total_bookings': bookings.count(),
        'pending': bookings.filter(status='pending').count(),
        'confirmed': bookings.filter(status='confirmed').count(),
        'completed': bookings.filter(status='completed').count(),
        'cancelled': bookings.filter(status='cancelled').count(),
        'upcoming_bookings': BookingSerializer(upcoming, many=True, context={'request': request}).data,
    })
