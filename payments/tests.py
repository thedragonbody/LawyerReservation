from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User, ClientProfile, LawyerProfile
from appointments.models import Appointment, TimeSlot
from payments.models import Payment
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta


class PaymentsAPITestCase(TestCase):
    def setUp(self):
        self.client_api = APIClient()

        # --------- ساخت یوزرها ---------
        self.client_user = User.objects.create_user(
            email="client@example.com",
            phone_number="+989111111111",
            first_name="Ali",
            last_name="Ahmadi",
            password="pass123"
        )
        self.lawyer_user = User.objects.create_user(
            email="lawyer@example.com",
            phone_number="+989222222222",
            first_name="Reza",
            last_name="Hosseini",
            password="pass123"
        )

        # پروفایل‌ها
        self.client_profile = ClientProfile.objects.create(user=self.client_user, national_id="1234567890")
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user, expertise="Family Law")

        # --------- ساخت Slot و Appointment ---------
        self.slot = TimeSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            is_booked=False
        )
        self.appointment = Appointment.objects.create(
            client=self.client_profile,
            lawyer=self.lawyer_profile,
            slot=self.slot,
            status=Appointment.Status.PENDING
        )

        # توکن ورود client
        self.client_api.force_authenticate(user=self.client_user)

    # ------------------ ایجاد پرداخت ------------------
    def test_create_payment(self):
        url = reverse("payment-create")
        data = {
            "appointment": self.appointment.id,
            "amount": 50000
        }
        response = self.client_api.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.first()
        self.assertEqual(payment.status, Payment.Status.PENDING)

    # ------------------ تایید پرداخت موفق ------------------
    @patch("payments.views.requests.post")
    def test_verify_payment_success(self, mock_post):
        payment = Payment.objects.create(
            user=self.client_user,
            appointment=self.appointment,
            amount=100000,
            status=Payment.Status.PENDING,
            transaction_id="tx123"
        )

        # شبیه‌سازی پاسخ موفق بانک
        mock_post.return_value.json.return_value = {"status": 100}

        url = reverse("payment-verify")
        response = self.client_api.post(url, {"transaction_id": "tx123"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.appointment.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.COMPLETED)
        self.assertEqual(self.appointment.status, Appointment.Status.CONFIRMED)

    # ------------------ تایید پرداخت ناموفق ------------------
    @patch("payments.views.requests.post")
    def test_verify_payment_failed(self, mock_post):
        payment = Payment.objects.create(
            user=self.client_user,
            appointment=self.appointment,
            amount=100000,
            status=Payment.Status.PENDING,
            transaction_id="tx456"
        )

        # شبیه‌سازی پاسخ ناموفق بانک
        mock_post.return_value.json.return_value = {"status": 101}

        url = reverse("payment-verify")
        response = self.client_api.post(url, {"transaction_id": "tx456"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)

    # ------------------ لیست پرداخت‌ها ------------------
    def test_list_payments(self):
        Payment.objects.create(
            user=self.client_user,
            appointment=self.appointment,
            amount=200000,
            status=Payment.Status.COMPLETED,
            transaction_id="tx789"
        )
        url = reverse("payment-list")
        response = self.client_api.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["transaction_id"], "tx789")