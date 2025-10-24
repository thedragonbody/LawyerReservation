from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from appointments.models import InPersonAppointment
from appointments.services.reminders import (
    ReminderDispatchResult,
    resolve_user_channel_preferences,
    send_reminder_to_user,
)
from client_profile.models import ClientProfile
from lawyer_profile.models import LawyerProfile
from notifications.models import Notification
from payments.models import Payment
from users.models import User
from rest_framework.test import APITestCase


class NotificationChannelPreferenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+989100000010",
            password="secret",
            first_name="Client",
        )
        self.profile = ClientProfile.objects.create(user=self.user)

    def test_default_channel_preferences_enabled(self):
        preferences = resolve_user_channel_preferences(self.user)
        self.assertTrue(preferences["push"])
        self.assertTrue(preferences["sms"])

    def test_channel_preferences_reflect_profile_flags(self):
        self.profile.receive_push_notifications = False
        self.profile.receive_sms_notifications = True
        self.profile.save()

        preferences = resolve_user_channel_preferences(self.user)
        self.assertFalse(preferences["push"])
        self.assertTrue(preferences["sms"])

    @patch("appointments.services.reminders.send_sms")
    @patch("appointments.services.reminders.Notification.send")
    def test_send_reminder_to_user_respects_preferences(
        self, mock_notification_send, mock_send_sms
    ):
        self.profile.receive_push_notifications = False
        self.profile.receive_sms_notifications = True
        self.profile.save()

        result = send_reminder_to_user(
            user=self.user,
            title="Test",
            message="Push message",
            sms_message="SMS message",
        )

        self.assertIsInstance(result, ReminderDispatchResult)
        self.assertFalse(result.push_sent)
        self.assertTrue(result.sms_sent)

        mock_notification_send.assert_not_called()
        mock_send_sms.assert_called_once_with(self.user.phone_number, "SMS message")

    @patch("appointments.services.reminders.send_sms")
    @patch("appointments.services.reminders.Notification.send")
    def test_send_reminder_to_user_uses_enabled_channels(
        self, mock_notification_send, mock_send_sms
    ):
        result = send_reminder_to_user(
            user=self.user,
            title="Hello",
            message="Push body",
            sms_message="SMS body",
        )

        self.assertTrue(result.push_sent)
        self.assertTrue(result.sms_sent)

        mock_notification_send.assert_called_once()
        mock_send_sms.assert_called_once_with(self.user.phone_number, "SMS body")


class InPersonPaymentNotificationTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            phone_number="+989130000001",
            password="secret",
            first_name="Client",
            is_active=True,
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.lawyer_user = User.objects.create_user(
            phone_number="+989130000002",
            password="secret",
            first_name="Lawyer",
            is_active=True,
        )
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        scheduled_for = timezone.now() + timezone.timedelta(days=3)
        self.inperson_appointment = InPersonAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            scheduled_for=scheduled_for,
            location="دفتر میدان ونک",
        )

        self.payment = Payment.objects.create(
            user=self.client_user,
            inperson_appointment=self.inperson_appointment,
            amount=Decimal("650000"),
            status=Payment.Status.PENDING,
        )

    @patch("appointments.models.send_sms")
    def test_inperson_payment_completion_creates_notifications(self, mock_send_sms):
        self.assertIn(
            Notification.Type.INPERSON_PAYMENT_SUCCESS,
            Notification.Type.values,
        )

        self.payment.mark_completed()

        expected_time = timezone.localtime(self.inperson_appointment.scheduled_for).strftime(
            "%Y-%m-%d %H:%M"
        )

        notifications = Notification.objects.filter(
            type=Notification.Type.INPERSON_PAYMENT_SUCCESS
        ).order_by("user_id")
        self.assertEqual(notifications.count(), 2)

        client_notification = next(n for n in notifications if n.user == self.client_user)
        lawyer_notification = next(n for n in notifications if n.user == self.lawyer_user)

        self.assertIn(expected_time, client_notification.message)
        self.assertIn(expected_time, lawyer_notification.message)

        self.assertEqual(mock_send_sms.call_count, 2)

    @patch("appointments.models.send_sms")
    def test_inperson_payment_refund_notifies_both_parties(self, mock_send_sms):
        self.payment.mark_completed()
        Notification.objects.all().delete()
        mock_send_sms.reset_mock()

        self.payment.mark_refunded()

        expected_time = timezone.localtime(self.inperson_appointment.scheduled_for).strftime(
            "%Y-%m-%d %H:%M"
        )

        notifications = Notification.objects.filter(
            type=Notification.Type.INPERSON_PAYMENT_REFUNDED
        )
        self.assertEqual(notifications.count(), 2)

        for notification in notifications:
            self.assertIn("بازگشت وجه", notification.title)
            self.assertIn(expected_time, notification.message)

        self.assertEqual(mock_send_sms.call_count, 2)

        self.assertEqual(
            {n.user for n in notifications},
            {self.client_user, self.lawyer_user},
        )


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+989120000000",
            password="secret",
            first_name="Client",
        )
        self.other_user = User.objects.create_user(
            phone_number="+989120000001",
            password="secret",
            first_name="Other",
        )

        Notification.objects.create(
            user=self.user,
            title="پیام ۱",
            message="متن",
            type=Notification.Type.GENERAL,
        )
        Notification.objects.create(
            user=self.other_user,
            title="پیام ۲",
            message="متن",
            type=Notification.Type.GENERAL,
        )

        self.client.force_authenticate(user=self.user)

    def test_list_notifications_returns_only_current_user(self):
        response = self.client.get("/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "پیام ۱")
        self.assertEqual(response.data[0]["status"], Notification.Status.UNREAD)

    def test_create_notification_sets_defaults(self):
        payload = {
            "title": "عنوان",
            "message": "متن",
            "type": Notification.Type.APPOINTMENT_REMINDER,
            "link": "https://example.com/detail",
        }

        response = self.client.post("/notifications/create/", data=payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["status"], Notification.Status.UNREAD)
        self.assertEqual(response.data["type"], Notification.Type.APPOINTMENT_REMINDER)
        self.assertEqual(response.data["link"], payload["link"])

    def test_mark_read_updates_status(self):
        notification = Notification.objects.create(
            user=self.user,
            title="خوانده شود",
            message="متن",
        )

        url = f"/notifications/{notification.id}/mark-read/"
        response = self.client.patch(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Notification.Status.READ)
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.READ)

    def test_delete_notification(self):
        notification = Notification.objects.create(
            user=self.user,
            title="حذف",
            message="متن",
        )

        url = f"/notifications/{notification.id}/delete/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Notification.objects.filter(id=notification.id).exists())
