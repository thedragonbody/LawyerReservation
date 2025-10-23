from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from appointments.models import OnlineAppointment, OnlineSlot
from lawyer_profile.models import LawyerProfile
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
        return OnlineAppointment.objects.filter(client__user=self.request.user).order_by('slot__start_time')

# -------------------------
# لیست رزروها برای Lawyer
# -------------------------
class LawyerDashboardView(generics.ListAPIView):
    serializer_class = LawyerAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OnlineAppointment.objects.filter(lawyer__user=self.request.user).order_by('slot__start_time')

# -------------------------
# آمار و نمودارهای داشبورد با فیلتر پیشرفته
# -------------------------

def calculate_tax(amount: Decimal) -> Decimal:
    # مثال: مالیات ثابت 10٪
    return amount * Decimal('0.10')

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # -------------------------
        # تعیین queryset بر اساس نوع کاربر
        # -------------------------
        if hasattr(user, 'client_profile'):
            qs = OnlineAppointment.objects.filter(client__user=user)
        elif hasattr(user, 'lawyer_profile'):
            qs = OnlineAppointment.objects.filter(lawyer__user=user)
        else:
            qs = OnlineAppointment.objects.none()

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
        sort_by = request.GET.get('sort_by')  # appointments | success_percent | revenue
        order = request.GET.get('order', 'desc')  # asc | desc

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
        status_percent = {s['status']: round(s['count'] / total_appointments * 100, 2) if total_appointments else 0
                          for s in status_counts}

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
            for lw in lawyer_counts:
                lw['success_percent'] = round(lw['confirmed'] / lw['total'] * 100, 2) if lw['total'] else 0

            if sort_by == 'appointments':
                lawyer_counts = sorted(lawyer_counts, key=lambda x: x['total'], reverse=(order=='desc'))
            elif sort_by == 'success_percent':
                lawyer_counts = sorted(lawyer_counts, key=lambda x: x['success_percent'], reverse=(order=='desc'))

            lawyer_counts = lawyer_counts[:5]
            for lw in lawyer_counts:
                top_lawyers.append({
                    'id': lw['lawyer__id'],
                    'name': f"{lw['lawyer__user__first_name']} {lw['lawyer__user__last_name']}",
                    'appointments': lw['total'],
                    'success_percent': lw['success_percent']
                })

        # -------------------------
        # ۵ مشتری پربازدید و درصد موفقیت (برای وکیل)
        # -------------------------
        top_clients = []
        if hasattr(user, 'lawyer_profile'):
            client_counts = qs.values('client__id', 'client__user__first_name', 'client__user__last_name') \
                              .annotate(total=Count('id'),
                                        confirmed=Count('id', filter=Q(status='CONFIRMED')))
            for cl in client_counts:
                cl['success_percent'] = round(cl['confirmed'] / cl['total'] * 100, 2) if cl['total'] else 0

            if sort_by == 'appointments':
                client_counts = sorted(client_counts, key=lambda x: x['total'], reverse=(order=='desc'))
            elif sort_by == 'success_percent':
                client_counts = sorted(client_counts, key=lambda x: x['success_percent'], reverse=(order=='desc'))

            client_counts = client_counts[:5]
            for cl in client_counts:
                top_clients.append({
                    'id': cl['client__id'],
                    'name': f"{cl['client__user__first_name']} {cl['client__user__last_name']}",
                    'appointments': cl['total'],
                    'success_percent': cl['success_percent']
                })

        # -------------------------
        # گزارش مالی ماهانه و مالیات (ویژه وکلا)
        # -------------------------
        monthly_income = {}
        monthly_sessions = {}
        monthly_tax = {}
        annual_income = Decimal(0)
        annual_tax = Decimal(0)

        if hasattr(user, 'lawyer_profile'):
            financial_qs = qs.filter(status__in=['CONFIRMED', 'COMPLETED'])
            if payment_type:
                financial_qs = financial_qs.filter(payment__payment_method__iexact=payment_type)

            for appt in financial_qs:
                month_key = appt.slot.start_time.strftime('%Y-%m')
                monthly_income[month_key] = monthly_income.get(month_key, Decimal(0)) + appt.slot.price
                monthly_sessions[month_key] = monthly_sessions.get(month_key, 0) + 1
                month_tax = calculate_tax(appt.slot.price)
                monthly_tax[month_key] = monthly_tax.get(month_key, Decimal(0)) + month_tax
                annual_income += appt.slot.price
                annual_tax += month_tax

            monthly_income = dict(sorted(monthly_income.items()))
            monthly_sessions = dict(sorted(monthly_sessions.items()))
            monthly_tax = dict(sorted(monthly_tax.items()))

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
            'top_clients': top_clients,
            'monthly_income': monthly_income,
            'monthly_sessions': monthly_sessions,
            'monthly_tax': monthly_tax,
            'annual_income': annual_income,
            'annual_tax': annual_tax,
        })