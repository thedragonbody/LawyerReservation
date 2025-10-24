from unittest.mock import patch

from django.test import TestCase

from appointments.services.reminders import (
    ReminderDispatchResult,
    resolve_user_channel_preferences,
    send_reminder_to_user,
)
from client_profile.models import ClientProfile
from users.models import User


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

