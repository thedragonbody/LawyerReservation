"""Utility services for dashboard analytics and filtering."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Q, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils.timezone import now

from django.core.exceptions import FieldDoesNotExist

from appointments.models import OnlineAppointment
from common.choices import AppointmentStatus
from payments.models import Payment
from rating_and_reviews.models import LawyerReview

User = get_user_model()


ZERO = Decimal("0.00")
TAX_RATE = Decimal("0.10")

try:
    OnlineAppointment._meta.get_field("session_type")
    HAS_SESSION_TYPE = True
except FieldDoesNotExist:
    HAS_SESSION_TYPE = False


@dataclass
class DashboardFilterParams:
    """Normalized filter parameters for dashboard queries."""

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    session_type: Optional[str] = None
    lawyer_id: Optional[int] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    payment_type: Optional[str] = None
    sort_by: Optional[str] = None
    order: str = "desc"

    @classmethod
    def from_request(cls, request) -> "DashboardFilterParams":
        """Create filters from a DRF/Django request object."""

        params: Dict[str, object] = {}

        def _parse_date(key: str) -> Optional[date]:
            raw = request.GET.get(key)
            if not raw:
                return None
            try:
                return date.fromisoformat(raw)
            except ValueError:
                return None

        params["start_date"] = _parse_date("start_date")
        params["end_date"] = _parse_date("end_date")

        status = request.GET.get("status")
        params["status"] = status.lower() if status else None

        session_type = request.GET.get("session_type")
        params["session_type"] = session_type.lower() if session_type else None

        lawyer_id = request.GET.get("lawyer_id")
        params["lawyer_id"] = int(lawyer_id) if lawyer_id else None

        def _parse_decimal(key: str) -> Optional[Decimal]:
            raw = request.GET.get(key)
            if not raw:
                return None
            try:
                return Decimal(raw)
            except (TypeError, ValueError):
                return None

        params["min_price"] = _parse_decimal("min_price")
        params["max_price"] = _parse_decimal("max_price")

        payment_type = request.GET.get("payment_type")
        params["payment_type"] = payment_type.lower() if payment_type else None

        params["sort_by"] = request.GET.get("sort_by")
        order = request.GET.get("order")
        if order in {"asc", "desc"}:
            params["order"] = order

        return cls(**params)


class DashboardAnalyticsService:
    """Aggregates appointment, payment and rating data for dashboards."""

    def __init__(self, user: User, filters: Optional[DashboardFilterParams] = None):
        self.user = user
        self.filters = filters or DashboardFilterParams()
        self._appointments = self._build_filtered_queryset()

    # ------------------------------------------------------------------
    # Queryset builders
    # ------------------------------------------------------------------
    def _base_queryset(self) -> OnlineAppointment.objects.__class__:
        if hasattr(self.user, "client_profile"):
            return OnlineAppointment.objects.filter(client__user=self.user)
        if hasattr(self.user, "lawyer_profile"):
            return OnlineAppointment.objects.filter(lawyer__user=self.user)
        return OnlineAppointment.objects.none()

    def _build_filtered_queryset(self) -> OnlineAppointment.objects.__class__:
        qs = self._base_queryset().select_related("slot", "lawyer__user", "client__user")

        if self.filters.start_date:
            qs = qs.filter(slot__start_time__date__gte=self.filters.start_date)
        if self.filters.end_date:
            qs = qs.filter(slot__start_time__date__lte=self.filters.end_date)
        if self.filters.status:
            qs = qs.filter(status__iexact=self.filters.status)
        if self.filters.session_type and HAS_SESSION_TYPE:
            qs = qs.filter(session_type__iexact=self.filters.session_type)
        if self.filters.lawyer_id:
            qs = qs.filter(lawyer__id=self.filters.lawyer_id)
        if self.filters.min_price is not None:
            qs = qs.filter(slot__price__gte=self.filters.min_price)
        if self.filters.max_price is not None:
            qs = qs.filter(slot__price__lte=self.filters.max_price)

        return qs

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def get_appointments(self):
        return self._appointments

    def get_payments(self):
        qs = Payment.objects.filter(appointment__in=self._appointments)
        if self.filters.payment_type:
            qs = qs.filter(payment_method__iexact=self.filters.payment_type)
        return qs.select_related("appointment")

    def get_ratings(self):
        if hasattr(self.user, "lawyer_profile"):
            return LawyerReview.objects.filter(relation__lawyer__user=self.user)
        if hasattr(self.user, "client_profile"):
            return LawyerReview.objects.filter(relation__client__user=self.user)
        return LawyerReview.objects.none()

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    def get_metrics(self) -> Dict[str, object]:
        appointments = self._appointments
        payments = self.get_payments()
        ratings = self.get_ratings()

        total_appointments = appointments.count()

        status_counts_qs = appointments.values("status").annotate(count=Count("id"))
        status_counts = list(status_counts_qs)
        status_percent = {
            item["status"]: round((item["count"] / total_appointments) * 100, 2)
            if total_appointments
            else 0.0
            for item in status_counts
        }

        confirmed_qs = appointments.filter(status=AppointmentStatus.CONFIRMED)
        successful_appointments = confirmed_qs.count()
        conversion_rate = (
            round((successful_appointments / total_appointments) * 100, 2)
            if total_appointments
            else 0.0
        )

        daily_appointments = self._build_daily_appointments_series(appointments)
        daily_revenue = self._build_daily_revenue_series(payments)

        top_lawyers = self._build_top_lawyers(appointments)
        top_clients = self._build_top_clients(appointments)

        monthly_income, monthly_sessions, monthly_tax = self._build_monthly_financials(payments)
        annual_income = sum(monthly_income.values(), ZERO)
        annual_tax = sum(monthly_tax.values(), ZERO)

        completed_payments = payments.filter(status=Payment.Status.COMPLETED)
        total_payments = completed_payments.aggregate(
            total=Coalesce(Sum("amount"), ZERO)
        )["total"]

        refunded_payments = payments.filter(status=Payment.Status.REFUNDED)
        total_refunds = refunded_payments.aggregate(
            total=Coalesce(Sum("amount"), ZERO)
        )["total"]

        avg_ticket = (
            (total_payments / successful_appointments)
            if successful_appointments
            else ZERO
        )

        payment_status_counts = {
            item["status"]: item["count"]
            for item in payments.values("status").annotate(count=Count("id"))
        }

        rating_agg = ratings.aggregate(avg=Avg("rating"), count=Count("id"))
        average_rating = (
            round(float(rating_agg["avg"]), 2) if rating_agg["avg"] is not None else None
        )
        rating_count = rating_agg["count"]

        return {
            "total_appointments": total_appointments,
            "status_counts": status_counts,
            "status_percent": status_percent,
            "daily_appointments": daily_appointments,
            "daily_revenue": daily_revenue,
            "top_lawyers": top_lawyers,
            "top_clients": top_clients,
            "monthly_income": monthly_income,
            "monthly_sessions": monthly_sessions,
            "monthly_tax": monthly_tax,
            "annual_income": annual_income,
            "annual_tax": annual_tax,
            "total_payments": total_payments,
            "total_refunds": total_refunds,
            "payment_status_counts": payment_status_counts,
            "conversion_rate": conversion_rate,
            "average_ticket_size": avg_ticket,
            "average_rating": average_rating,
            "rating_count": rating_count,
        }

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------
    def iter_export_rows(self) -> Iterable[Tuple]:
        """Yield rows suitable for CSV/Excel exports."""

        yield (
            "Appointment ID",
            "Client",
            "Lawyer",
            "Status",
            "Session Type",
            "Start Time",
            "Price",
            "Payment Total",
        )

        payments_by_appointment = {
            item["appointment"]: item["total"]
            for item in self.get_payments()
            .filter(status=Payment.Status.COMPLETED)
            .values("appointment")
            .annotate(total=Coalesce(Sum("amount"), ZERO))
        }

        for appointment in self._appointments.order_by("slot__start_time"):
            yield (
                appointment.id,
                appointment.client.user.get_full_name(),
                appointment.lawyer.user.get_full_name(),
                appointment.status,
                getattr(appointment, "session_type", None),
                appointment.slot.start_time.isoformat(),
                appointment.slot.price,
                payments_by_appointment.get(appointment.id, ZERO),
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _build_daily_appointments_series(self, appointments) -> Dict[str, int]:
        last_30_days = [now().date() - timedelta(days=i) for i in range(29, -1, -1)]
        base = {day.isoformat(): 0 for day in last_30_days}
        counts = (
            appointments
            .annotate(day=TruncDate("slot__start_time"))
            .values("day")
            .annotate(count=Count("id"))
        )
        for item in counts:
            if item["day"]:
                base[item["day"].isoformat()] = item["count"]
        return base

    def _build_daily_revenue_series(self, payments) -> Dict[str, Decimal]:
        last_30_days = [now().date() - timedelta(days=i) for i in range(29, -1, -1)]
        base = {day.isoformat(): ZERO for day in last_30_days}
        completed = payments.filter(status=Payment.Status.COMPLETED)
        totals = (
            completed
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Coalesce(Sum("amount"), ZERO))
        )
        for item in totals:
            if item["day"]:
                base[item["day"].isoformat()] = item["total"]
        return base

    def _build_top_lawyers(self, appointments) -> List[Dict[str, object]]:
        if not hasattr(self.user, "client_profile"):
            return []

        lawyer_counts = (
            appointments
            .values(
                "lawyer__id",
                "lawyer__user__first_name",
                "lawyer__user__last_name",
            )
            .annotate(
                appointments=Count("id"),
                confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
                revenue=Coalesce(Sum("payments__amount", filter=Q(payments__status=Payment.Status.COMPLETED)), ZERO),
            )
        )

        entries = [
            {
                "id": item["lawyer__id"],
                "name": f"{item['lawyer__user__first_name']} {item['lawyer__user__last_name']}",
                "appointments": item["appointments"],
                "success_percent": round(
                    (item["confirmed"] / item["appointments"]) * 100, 2
                ) if item["appointments"] else 0.0,
                "total_revenue": item["revenue"],
            }
            for item in lawyer_counts
        ]

        return self._sort_and_limit(entries)

    def _build_top_clients(self, appointments) -> List[Dict[str, object]]:
        if not hasattr(self.user, "lawyer_profile"):
            return []

        client_counts = (
            appointments
            .values(
                "client__id",
                "client__user__first_name",
                "client__user__last_name",
            )
            .annotate(
                appointments=Count("id"),
                confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
                revenue=Coalesce(Sum("payments__amount", filter=Q(payments__status=Payment.Status.COMPLETED)), ZERO),
            )
        )

        entries = [
            {
                "id": item["client__id"],
                "name": f"{item['client__user__first_name']} {item['client__user__last_name']}",
                "appointments": item["appointments"],
                "success_percent": round(
                    (item["confirmed"] / item["appointments"]) * 100, 2
                ) if item["appointments"] else 0.0,
                "total_revenue": item["revenue"],
            }
            for item in client_counts
        ]

        return self._sort_and_limit(entries)

    def _sort_and_limit(self, entries: List[Dict[str, object]]) -> List[Dict[str, object]]:
        if not entries:
            return []

        sort_key = self.filters.sort_by or "appointments"
        reverse = self.filters.order != "asc"

        valid_keys = {"appointments", "success_percent", "total_revenue"}
        if sort_key not in valid_keys:
            sort_key = "appointments"

        entries.sort(key=lambda item: item.get(sort_key, 0) or 0, reverse=reverse)
        return entries[:5]

    def _build_monthly_financials(self, payments):
        completed = payments.filter(status=Payment.Status.COMPLETED)
        monthly_income: Dict[str, Decimal] = {}
        monthly_sessions: Dict[str, int] = {}
        monthly_tax: Dict[str, Decimal] = {}

        aggregates = (
            completed
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(
                income=Coalesce(Sum("amount"), ZERO),
                sessions=Count("appointment", distinct=True),
            )
        )

        for item in aggregates:
            if not item["month"]:
                continue
            key = item["month"].strftime("%Y-%m")
            income = item["income"]
            monthly_income[key] = income
            monthly_sessions[key] = item["sessions"]
            monthly_tax[key] = (income * TAX_RATE).quantize(Decimal("0.01"))

        return monthly_income, monthly_sessions, monthly_tax


def get_filtered_appointments(user: User, request) -> OnlineAppointment.objects.__class__:
    """Convenience helper for list views to reuse the filtering logic."""

    filters = DashboardFilterParams.from_request(request)
    service = DashboardAnalyticsService(user, filters)
    return service.get_appointments().order_by("slot__start_time")
