from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from appointments.models import OnlineAppointment, OnlineSlot
from appointments.tasks import send_appointment_reminders_task
from client_profile.models import ClientProfile
from common.choices import AppointmentStatus
from lawyer_profile.models import LawyerProfile
from users.models import User


class AppointmentReminderTaskTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            phone_number="+989100000001",
            password="secret",
            first_name="Client",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.lawyer_user = User.objects.create_user(
            phone_number="+989100000002",
            password="secret",
            first_name="Lawyer",
        )
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        slot_start = timezone.now() + timedelta(minutes=30)
        slot_end = slot_start + timedelta(minutes=30)
        self.slot = OnlineSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=slot_start,
            end_time=slot_end,
        )
        self.appointment = OnlineAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            slot=self.slot,
            status=AppointmentStatus.CONFIRMED,
        )

    @patch("appointments.services.reminders.send_sms")
    @patch("appointments.services.reminders.Notification.send")
    def test_send_appointment_reminders_task_uses_slot_start_time(
        self, mock_notification_send, mock_send_sms
    ):
        processed = send_appointment_reminders_task()

        self.assertEqual(processed, 1)
        self.appointment.refresh_from_db()
        self.assertTrue(self.appointment.is_reminder_sent)

        expected_time = timezone.localtime(self.slot.start_time).strftime("%Y-%m-%d %H:%M")

        # Client notification contains slot start time
        client_calls = [
            sms_call
            for sms_call in mock_send_sms.call_args_list
            if sms_call.args[0] == self.client_user.phone_number
        ]
        self.assertEqual(len(client_calls), 1)
        self.assertIn(expected_time, client_calls[0].args[1])

        # Two push notifications (client and lawyer)
        self.assertEqual(mock_notification_send.call_count, 2)

    @patch("appointments.services.reminders.send_sms")
    @patch("appointments.services.reminders.Notification.send")
    def test_send_appointment_reminders_respects_client_channel_preferences(
        self, mock_notification_send, mock_send_sms
    ):
        self.client_profile.receive_push_notifications = False
        self.client_profile.receive_sms_notifications = False
        self.client_profile.save()

        send_appointment_reminders_task()

        # No SMS or push for the client when disabled
        client_sms_calls = [
            sms_call
            for sms_call in mock_send_sms.call_args_list
            if sms_call.args[0] == self.client_user.phone_number
        ]
        self.assertEqual(client_sms_calls, [])

        client_push_calls = [
            push_call
            for push_call in mock_notification_send.call_args_list
            if push_call.kwargs.get("user") == self.client_user
        ]
        self.assertEqual(client_push_calls, [])

        # Lawyer should still receive notifications
        lawyer_sms_calls = [
            sms_call
            for sms_call in mock_send_sms.call_args_list
            if sms_call.args[0] == self.lawyer_user.phone_number
        ]
        self.assertEqual(len(lawyer_sms_calls), 1)

        lawyer_push_calls = [
            push_call
            for push_call in mock_notification_send.call_args_list
            if push_call.kwargs.get("user") == self.lawyer_user
        ]
        self.assertEqual(len(lawyer_push_calls), 1)
