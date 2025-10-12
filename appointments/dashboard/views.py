from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from appointments.models import Appointment, Slot
from users.models import LawyerProfile
from django.db.models import Count, Sum
from django.utils.timezone import now, timedelta
from collections import defaultdict
from decimal import Decimal
from .serializers import ClientAppointmentSerializer, LawyerAppointmentSerializer
from datetime import datetime
from django.db.models import Count, Sum, Q

# -------------------------
# لیست رزروها برای Client
# -------------------------
class ClientDashboardView(generics.ListAPIView):
    serializer_class = ClientAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(client__user=self.request.user).order_by('slot__start_time')

# -------------------------
# لیست رزروها برای Lawyer
# -------------------------
class LawyerDashboardView(generics.ListAPIView):
    serializer_class = LawyerAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(lawyer__user=self.request.user).order_by('slot__start_time')

# -------------------------
# آمار و نمودارهای داشبورد با فیلتر پیشرفته
# -------------------------
class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # -------------------------
        # تعیین queryset بر اساس نوع کاربر
        # -------------------------
        if hasattr(user, 'client_profile'):
            qs = Appointment.objects.filter(client__user=user)
        elif hasattr(user, 'lawyer_profile'):
            qs = Appointment.objects.filter(lawyer__user=user)
        else:
            qs = Appointment.objects.none()

        # -------------------------
        # فیلترهای GET
        # -------------------------
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        status = request.GET.get('status')
        lawyer_id = request.GET.get('lawyer_id')
        session_type = request.GET.get('session_type')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        payment_type = request.GET.get('payment_type')
        sort_lawyer_by_appointments = request.GET.get('sort_lawyer', 'false').lower() == 'true'

        if start_date:
            try:
                start_date_obj = datetime.fromisoformat(start_date).date()
                qs = qs.filter(slot__start_time__date__gte=start_date_obj)
            except ValueError:
                pass

        if end_date:
            try:
                end_date_obj = datetime.fromisoformat(end_date).date()
                qs = qs.filter(slot__start_time__date__lte=end_date_obj)
            except ValueError:
                pass

        if status:
            qs = qs.filter(status=status.upper())
        if lawyer_id:
            qs = qs.filter(lawyer__id=lawyer_id)
        if session_type:
            qs = qs.filter(session_type=session_type.upper())
        if min_price:
            qs = qs.filter(slot__price__gte=Decimal(min_price))
        if max_price:
            qs = qs.filter(slot__price__lte=Decimal(max_price))
        if payment_type:
            qs = qs.filter(payment__payment_method__iexact=payment_type)

        # -------------------------
        # محاسبه تعداد جلسات و درصدها
        # -------------------------
        total_appointments = qs.count()
        status_counts = qs.values('status').annotate(count=Count('id'))
        status_percent = {}
        for s in status_counts:
            status_percent[s['status']] = round(s['count'] / total_appointments * 100, 2) if total_appointments else 0

        # -------------------------
        # Trend جلسات روزانه و نمودار درآمد (آخر 30 روز)
        # -------------------------
        today = now().date()
        last_30_days = [today - timedelta(days=i) for i in range(30)]
        daily_appointments = defaultdict(int)
        daily_revenue = defaultdict(Decimal)
        confirmed_qs = qs.filter(status='CONFIRMED')

        for day in last_30_days:
            daily_appointments[str(day)] = qs.filter(slot__start_time__date=day).count()
            daily_revenue[str(day)] = confirmed_qs.filter(slot__start_time__date=day).aggregate(
                total=Sum('slot__price'))['total'] or Decimal(0)

        # -------------------------
        # ۵ وکیل پربازدید و درصد موفقیت (برای مشتری)
        # -------------------------
        top_lawyers = []
        if hasattr(user, 'client_profile'):
            lawyer_counts = qs.values('lawyer__id', 'lawyer__user__first_name', 'lawyer__user__last_name') \
                              .annotate(total=Count('id'),
                                        confirmed=Count('id', filter=Q(status='CONFIRMED')))
            if sort_lawyer_by_appointments:
                lawyer_counts = lawyer_counts.order_by('-total')[:5]
            else:
                lawyer_counts = lawyer_counts[:5]

            for lw in lawyer_counts:
                percent_success = round(lw['confirmed'] / lw['total'] * 100, 2) if lw['total'] else 0
                top_lawyers.append({
                    'id': lw['lawyer__id'],
                    'name': f"{lw['lawyer__user__first_name']} {lw['lawyer__user__last_name']}",
                    'appointments': lw['total'],
                    'success_percent': percent_success
                })

        # -------------------------
        # ۵ مشتری پربازدید و درصد موفقیت (برای وکیل)
        # -------------------------
        top_clients = []
        if hasattr(user, 'lawyer_profile'):
            client_counts = qs.values('client__id', 'client__user__first_name', 'client__user__last_name') \
                              .annotate(total=Count('id'),
                                        confirmed=Count('id', filter=Q(status='CONFIRMED'))) \
                              .order_by('-total')[:5]

            for cl in client_counts:
                percent_success = round(cl['confirmed'] / cl['total'] * 100, 2) if cl['total'] else 0
                top_clients.append({
                    'id': cl['client__id'],
                    'name': f"{cl['client__user__first_name']} {cl['client__user__last_name']}",
                    'appointments': cl['total'],
                    'success_percent': percent_success
                })

        # -------------------------
        # پاسخ JSON نهایی
        # -------------------------
        return Response({
            'total_appointments': total_appointments,
            'status_counts': list(status_counts),
            'status_percent': status_percent,
            'daily_appointments': dict(daily_appointments),
            'daily_revenue': dict(daily_revenue),
            'top_lawyers': top_lawyers,
            'top_clients': top_clients
        })