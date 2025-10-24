from decimal import Decimal

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import InPersonAppointment, OnlineAppointment, OnlineSlot
from client_profile.models import ClientProfile
from common.choices import AppointmentStatus
from lawyer_profile.models import LawyerProfile
from notifications.models import Notification
from payments.models import Payment, Wallet
from users.models import User


class WalletIntegrationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone_number="09120000000", password="pass1234", is_active=True)
        self.client.force_authenticate(self.user)

    def test_wallet_top_up_increases_balance(self):
        url = reverse("payments:wallet-top-up")
        response = self.client.post(url, {"amount": "100000"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal("100000"))
        self.assertEqual(wallet.reserved_balance, Decimal("0"))
        self.assertEqual(response.data["balance"], "100000.00")
        self.assertEqual(response.data["available_balance"], "100000.00")

    def test_reserve_capture_and_refund_flow(self):
        # Top-up first
        topup_url = reverse("payments:wallet-top-up")
        self.client.post(topup_url, {"amount": "150000"}, format="json")

        payment = Payment.objects.create(
            user=self.user,
            amount=Decimal("50000"),
            payment_method=Payment.Method.WALLET,
        )

        reserve_url = reverse("payments:wallet-reserve")
        response = self.client.post(reserve_url, {"payment_id": payment.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reserved_amount"], "50000.00")

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal("150000"))
        self.assertEqual(wallet.reserved_balance, Decimal("50000"))
        self.assertEqual(wallet.available_balance, Decimal("100000"))

        payment.refresh_from_db()
        self.assertEqual(payment.wallet_reserved_amount, Decimal("50000"))

        # Capture funds when payment is completed
        payment.mark_completed()
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("100000"))
        self.assertEqual(wallet.reserved_balance, Decimal("0"))

        # Refund payment back to wallet
        payment.mark_refunded()
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("150000"))
        self.assertEqual(wallet.reserved_balance, Decimal("0"))


class PaymentCreationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="09120000001", password="pass1234", is_active=True
        )
        self.client.force_authenticate(self.user)

        self.client_profile = ClientProfile.objects.create(user=self.user)

        lawyer_user = User.objects.create_user(
            phone_number="09120000002", password="pass1234", is_active=True
        )
        self.lawyer_profile = LawyerProfile.objects.create(user=lawyer_user)

        start_time = timezone.now() + timezone.timedelta(days=1)
        end_time = start_time + timezone.timedelta(minutes=30)
        self.slot = OnlineSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=start_time,
            end_time=end_time,
            price=Decimal("500000"),
        )

        self.appointment = OnlineAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            slot=self.slot,
        )

        Payment.objects.create(
            user=self.user,
            appointment=self.appointment,
            amount=Decimal("500000"),
            status=Payment.Status.COMPLETED,
        )

    def test_duplicate_payment_request_returns_error(self):
        url = reverse("payments:payment-create")
        response = self.client.post(
            url,
            {"appointment_id": self.appointment.id, "amount": "500000"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "Payment already completed for this appointment."
        )
        self.assertEqual(
            Payment.objects.filter(appointment=self.appointment).count(),
            1,
        )


class InPersonPaymentFlowTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            phone_number="09120000010",
            password="pass1234",
            is_active=True,
            first_name="Client",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.lawyer_user = User.objects.create_user(
            phone_number="09120000011",
            password="pass1234",
            is_active=True,
            first_name="Lawyer",
        )
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        scheduled_for = timezone.now() + timezone.timedelta(days=2)
        self.inperson_appointment = InPersonAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            scheduled_for=scheduled_for,
            location="دفتر مرکزی",
        )

        self.payment = Payment.objects.create(
            user=self.client_user,
            amount=Decimal("750000"),
            inperson_appointment=self.inperson_appointment,
            status=Payment.Status.PENDING,
        )

    @patch("appointments.models.send_sms")
    def test_mark_completed_updates_status_and_notifies(self, mock_send_sms):
        self.payment.mark_completed()

        self.inperson_appointment.refresh_from_db()
        self.assertEqual(self.inperson_appointment.status, AppointmentStatus.PAID)

        notifications = Notification.objects.filter(
            type=Notification.Type.INPERSON_PAYMENT_SUCCESS
        )
        self.assertEqual(notifications.count(), 2)
        notified_users = {n.user for n in notifications}
        self.assertSetEqual(notified_users, {self.client_user, self.lawyer_user})

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)

        self.assertEqual(mock_send_sms.call_count, 2)

    @patch("appointments.models.send_sms")
    def test_mark_refunded_rolls_back_status_and_notifies(self, mock_send_sms):
        self.payment.mark_completed()
        mock_send_sms.reset_mock()

        self.payment.mark_refunded()

        self.inperson_appointment.refresh_from_db()
        self.assertEqual(self.inperson_appointment.status, AppointmentStatus.PENDING)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.REFUNDED)

        notifications = Notification.objects.filter(
            type=Notification.Type.INPERSON_PAYMENT_REFUNDED
        )
        self.assertEqual(notifications.count(), 2)
        notified_users = {n.user for n in notifications}
        self.assertSetEqual(notified_users, {self.client_user, self.lawyer_user})

        self.assertEqual(mock_send_sms.call_count, 2)


class IDPayCallbackTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="09120000020",
            password="pass1234",
            is_active=True,
        )
        self.other_user = User.objects.create_user(
            phone_number="09120000021",
            password="pass1234",
            is_active=True,
        )
        self.url = reverse("payments:idpay-callback")

    def test_success_callback_updates_payment_without_authentication(self):
        payment = Payment.objects.create(
            user=self.user,
            amount=Decimal("123000"),
            payment_method=Payment.Method.IDPAY,
        )

        payload = {
            "order_id": str(payment.id),
            "status": 100,
            "track_id": "TRK-SUCCESS",
            "user": self.other_user.id,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.COMPLETED)
        self.assertEqual(payment.transaction_id, "TRK-SUCCESS")
        self.assertEqual(payment.user, self.user)
        self.assertEqual(response.data["status"], Payment.Status.COMPLETED)
        self.assertEqual(payment.provider_data.get("track_id"), "TRK-SUCCESS")

    def test_failed_callback_marks_payment_failed_and_preserves_user(self):
        payment = Payment.objects.create(
            user=self.user,
            amount=Decimal("456000"),
            payment_method=Payment.Method.IDPAY,
        )

        payload = {
            "order_id": str(payment.id),
            "status": -1,
            "track_id": "TRK-FAIL",
            "user": self.other_user.id,
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(payment.transaction_id, "TRK-FAIL")
        self.assertEqual(payment.user, self.user)
        self.assertEqual(response.data["status"], Payment.Status.FAILED)
        self.assertEqual(payment.provider_data.get("status"), -1)
        self.assertEqual(payment.provider_data.get("track_id"), "TRK-FAIL")

class OnlinePaymentRefundFlowTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            phone_number="09120000020",
            password="pass1234",
            is_active=True,
            first_name="Client",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.lawyer_user = User.objects.create_user(
            phone_number="09120000021",
            password="pass1234",
            is_active=True,
            first_name="Lawyer",
        )
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        start_time = timezone.now() + timezone.timedelta(days=2)
        end_time = start_time + timezone.timedelta(minutes=30)
        self.slot = OnlineSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=start_time,
            end_time=end_time,
            price=Decimal("500000"),
        )

        self.appointment = OnlineAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            slot=self.slot,
        )

        self.payment = Payment.objects.create(
            user=self.client_user,
            amount=Decimal("500000"),
            appointment=self.appointment,
            status=Payment.Status.PENDING,
        )

    @patch("appointments.models.send_sms")
    def test_mark_refunded_cancels_online_appointment(self, mock_send_sms):
        self.payment.mark_completed()

        # پاک‌سازی نوتیفیکیشن‌ها و ریست فراخوانی SMS برای مرحله بازپرداخت
        Notification.objects.all().delete()
        mock_send_sms.reset_mock()

        self.payment.mark_refunded()

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.REFUNDED)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CANCELLED)

        self.slot.refresh_from_db()
        self.assertFalse(self.slot.is_booked)

        notifications = Notification.objects.all()
        self.assertEqual(notifications.count(), 2)
        notification_titles = {n.title for n in notifications}
        self.assertSetEqual(notification_titles, {"رزرو لغو شد", "رزرو کاربر لغو شد"})

        self.assertEqual(mock_send_sms.call_count, 2)
