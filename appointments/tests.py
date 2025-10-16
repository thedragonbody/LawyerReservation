from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from appointments.models import Slot, Appointment, AppointmentStatus
from datetime import datetime, timedelta
from unittest.mock import patch
from payments.models import Payment
from users.models import LawyerProfile, ClientProfile  # فرض شده اینجا هستند

User = get_user_model()

class AppointmentsFullTest(APITestCase):

    def setUp(self):
        # ------------------ USERS ------------------
        self.client_user = User.objects.create_user(phone_number="09901234567", password="testpass")
        self.lawyer_user = User.objects.create_user(phone_number="09907654321", password="testpass")

        # ساخت پروفایل‌ها به‌صورت دستی
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        # احراز هویت کاربر client برای تست‌ها
        self.client.force_authenticate(user=self.client_user)

        # ------------------ SLOTS ------------------
        self.slot1 = Slot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=datetime.now() + timedelta(days=1),
            is_booked=False
        )
        self.slot2 = Slot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=datetime.now() + timedelta(days=2),
            is_booked=False
        )

    # ------------------ SLOT TESTS ------------------
    def test_list_slots(self):
        url = reverse("appointments:slot-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_duplicate_slot_for_same_lawyer(self):
        url = reverse("appointments:slot-create")
        self.client.force_authenticate(user=self.lawyer_user)
        data = {"start_time": self.slot1.start_time}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------ APPOINTMENT TESTS ------------------
    def test_create_appointment_success(self):
        url = reverse("appointments:appointment-create")
        response = self.client.post(url, {"slot_id": self.slot1.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment_id = response.data.get("payment_id")
        self.assertIsNotNone(payment_id)
        payment = Payment.objects.get(id=payment_id)
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_create_appointment_slot_already_booked(self):
        self.slot1.is_booked = True
        self.slot1.save()
        url = reverse("appointments:appointment-create")
        response = self.client.post(url, {"slot_id": self.slot1.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Slot already booked", str(response.data))

    # ------------------ PAYMENT CALLBACK TESTS ------------------
    @patch("appointments.views.verify_payment_request")
    @patch("appointments.views.send_sms")
    def test_payment_callback_success(self, mock_send_sms, mock_verify_payment):
        payment = Payment.objects.create(
            user=self.client_user,
            amount=100,
            transaction_id="TX12345",
            status=Payment.Status.PENDING
        )
        mock_verify_payment.return_value = {"status": 100, "order_id": f"order_{self.slot1.id}"}
        url = reverse("appointments:payment-callback")
        response = self.client.post(url, {"transaction_id": payment.transaction_id}, format="json")

        payment.refresh_from_db()
        self.slot1.refresh_from_db()
        appointment = Appointment.objects.get(transaction_id=payment.transaction_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payment.status, Payment.Status.COMPLETED)
        self.assertTrue(self.slot1.is_booked)
        self.assertEqual(appointment.status, AppointmentStatus.CONFIRMED)
        mock_send_sms.assert_called_once()

    @patch("appointments.views.verify_payment_request")
    def test_payment_callback_failed(self, mock_verify_payment):
        payment = Payment.objects.create(
            user=self.client_user,
            amount=100,
            transaction_id="TX54321",
            status=Payment.Status.PENDING
        )
        mock_verify_payment.return_value = {"status": 0, "order_id": f"order_{self.slot2.id}"}
        url = reverse("appointments:payment-callback")
        response = self.client.post(url, {"transaction_id": payment.transaction_id}, format="json")
        payment.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(payment.status, Payment.Status.FAILED)

    @patch("appointments.views.verify_payment_request")
    def test_payment_callback_slot_already_booked(self, mock_verify_payment):
        self.slot1.is_booked = True
        self.slot1.save()
        payment = Payment.objects.create(
            user=self.client_user,
            amount=100,
            transaction_id="TX67890",
            status=Payment.Status.PENDING
        )
        mock_verify_payment.return_value = {"status": 100, "order_id": f"order_{self.slot1.id}"}
        url = reverse("appointments:payment-callback")
        response = self.client.post(url, {"transaction_id": payment.transaction_id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Slot already booked", str(response.data))

    def test_payment_callback_unauthorized_user(self):
        other_user = User.objects.create_user(phone_number="09909999999", password="testpass")
        other_client_profile = ClientProfile.objects.create(user=other_user)
        payment = Payment.objects.create(
            user=other_user,
            amount=100,
            transaction_id="TX99999",
            status=Payment.Status.PENDING
        )
        url = reverse("appointments:payment-callback")
        response = self.client.post(url, {"transaction_id": payment.transaction_id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)