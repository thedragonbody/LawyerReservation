from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import OnlineAppointment, OnlineSlot
from client_profile.models import ClientProfile
from common.choices import AppointmentStatus
from common.models import LawyerClientRelation
from lawyer_profile.models import LawyerProfile
from payments.models import Payment
from rating_and_reviews.models import LawyerReview
from users.models import User


class DashboardAPITests(APITestCase):
    def setUp(self):
        self.lawyer_user = User.objects.create_user(
            phone_number="09120000000",
            password="password",
            first_name="Law",
            last_name="Yer",
            is_active=True,
        )
        self.client_user = User.objects.create_user(
            phone_number="09120000001",
            password="password",
            first_name="Cli",
            last_name="Ent",
            is_active=True,
        )

        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        now = timezone.now()
        self.slot_confirmed = OnlineSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
            price=Decimal("500000"),
        )
        self.slot_pending = OnlineSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
            price=Decimal("400000"),
        )

        self.confirmed_appointment = OnlineAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            slot=self.slot_confirmed,
            status=AppointmentStatus.CONFIRMED,
        )
        self.pending_appointment = OnlineAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            slot=self.slot_pending,
            status=AppointmentStatus.PENDING,
        )

        Payment.objects.create(
            user=self.client_user,
            amount=Decimal("500000.00"),
            payment_method="idpay",
            status=Payment.Status.COMPLETED,
            appointment=self.confirmed_appointment,
        )

        self.relation = LawyerClientRelation.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
        )
        LawyerReview.objects.create(
            relation=self.relation,
            rating=4,
            comment="Great session",
        )

    def test_lawyer_dashboard_stats_returns_expected_metrics(self):
        self.client.force_authenticate(self.lawyer_user)
        url = reverse("dashboard-stats")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["total_appointments"], 2)
        self.assertIn("payment_status_counts", data)
        self.assertEqual(data["payment_status_counts"].get(Payment.Status.COMPLETED), 1)
        self.assertEqual(data["rating_count"], 1)
        self.assertAlmostEqual(float(data["conversion_rate"]), 50.0)
        self.assertTrue(any(item["appointments"] == 1 for item in data["top_clients"]))

    def test_stats_filters_by_status(self):
        self.client.force_authenticate(self.lawyer_user)
        url = reverse("dashboard-stats")
        response = self.client.get(url, {"status": AppointmentStatus.PENDING})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total_appointments"], 1)
        self.assertEqual(data["payment_status_counts"].get(Payment.Status.COMPLETED), None)

    def test_dashboard_export_csv(self):
        self.client.force_authenticate(self.lawyer_user)
        url = reverse("dashboard-export")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("Appointment ID", response.content.decode("utf-8"))

    def test_client_dashboard_filtered_queryset(self):
        self.client.force_authenticate(self.client_user)
        url = reverse("client-dashboard")
        response = self.client.get(
            url,
            {
                "status": AppointmentStatus.CONFIRMED,
                "start_date": self.slot_confirmed.start_time.date().isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["status"], AppointmentStatus.CONFIRMED)
