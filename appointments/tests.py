from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from rest_framework.test import APIClient

from appointments.integrations import CalendarService, CalendarSyncError
from appointments.models import (
    OnlineAppointment,
    OnlineSlot,
    OnsiteAppointment,
    OnsiteSlot,
)
from appointments.tasks import refresh_expiring_oauth_tokens, send_appointment_reminders_task
from appointments.utils import create_meeting_link
from client_profile.models import ClientProfile
from common.choices import AppointmentStatus
from lawyer_profile.models import LawyerProfile
from users.models import OAuthToken, User


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


class MeetingLinkGenerationTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            phone_number="+989120000003",
            password="secret",
            first_name="Client",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.lawyer_user = User.objects.create_user(
            phone_number="+989120000004",
            password="secret",
            first_name="Lawyer",
        )
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        slot_start = timezone.now() + timedelta(days=1)
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
        )

    def test_jitsi_provider_generates_link(self):
        link = create_meeting_link(self.appointment, provider="jitsi")
        self.assertTrue(link.startswith("https://meet.jit.si/"))

    @patch("appointments.utils.CalendarService")
    def test_google_provider_uses_calendar_service(self, mock_calendar_service):
        mock_instance = mock_calendar_service.return_value
        mock_instance.create_event.return_value = "google-42-1693412"

        link = create_meeting_link(self.appointment, provider="google")

        mock_calendar_service.assert_called_once_with(provider="google")
        mock_instance.create_event.assert_called_once_with(self.appointment)
        self.assertTrue(link.startswith("https://meet.google.com/"))
        slug = link.split("/")[-1]
        self.assertEqual(slug.count("-"), 2)


class OnsiteAppointmentSignalTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            phone_number="+989130000005",
            password="secret",
            first_name="Client",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.lawyer_user = User.objects.create_user(
            phone_number="+989130000006",
            password="secret",
            first_name="Lawyer",
            last_name="Office",
        )
        self.lawyer_profile = LawyerProfile.objects.create(
            user=self.lawyer_user,
            office_address="Tehran, Valiasr St.",
            office_latitude=35.123456,
            office_longitude=51.123456,
        )

        start = timezone.now() + timedelta(hours=2)
        end = start + timedelta(minutes=45)
        self.slot = OnsiteSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=start,
            end_time=end,
        )

    def test_booking_marks_slot_as_booked(self):
        appointment = OnsiteAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            slot=self.slot,
        )
        self.slot.refresh_from_db()
        self.assertEqual(appointment.status, AppointmentStatus.PENDING)
        self.assertTrue(self.slot.is_booked)

    def test_cancelling_frees_slot(self):
        appointment = OnsiteAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            slot=self.slot,
        )
        appointment.status = AppointmentStatus.CANCELLED
        appointment.save(update_fields=["status"])
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.is_booked)

    def test_prevent_double_booking_same_slot(self):
        OnsiteAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            slot=self.slot,
        )
        with self.assertRaises(ValidationError):
            OnsiteAppointment.objects.create(
                lawyer=self.lawyer_profile,
                client=self.client_profile,
                slot=self.slot,
            )

    def test_prevent_overlapping_slots(self):
        with self.assertRaises(ValidationError):
            OnsiteSlot.objects.create(
                lawyer=self.lawyer_profile,
                start_time=self.slot.start_time + timedelta(minutes=10),
                end_time=self.slot.end_time + timedelta(minutes=10),
            )

    @patch("appointments.utils.CalendarService")
    def test_google_provider_falls_back_to_temp_link(self, mock_calendar_service):
        mock_instance = mock_calendar_service.return_value
        mock_instance.create_event.side_effect = CalendarSyncError("token missing")

        link = create_meeting_link(self.appointment, provider="google")

        mock_calendar_service.assert_called_once_with(provider="google")
        mock_instance.create_event.assert_called_once_with(self.appointment)
        self.assertTrue(link.startswith("https://meet.google.com/"))
        slug = link.split("/")[-1]
        self.assertEqual(slug.count("-"), 2)


class CalendarOAuthFlowTests(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.lawyer_user = User.objects.create_user(
            phone_number="+989140000007",
            password="secret",
            first_name="OAuth",
            last_name="Lawyer",
        )
        self.api_client.force_authenticate(user=self.lawyer_user)
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

    @patch("appointments.integrations.oauth.requests.post")
    def test_oauth_callback_encrypts_token_and_enables_calendar_sync(self, mock_post):
        start_url = reverse("appointments:calendar-oauth-start", args=["google"])
        response = self.api_client.get(start_url)
        self.assertEqual(response.status_code, 200)
        state = response.data["state"]

        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.json.return_value = {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/calendar.events",
            "token_type": "Bearer",
        }

        callback_url = reverse("appointments:calendar-oauth-callback", args=["google"])
        callback_response = self.api_client.get(
            callback_url,
            {"code": "auth-code", "state": state},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(callback_response.status_code, 200)
        token = OAuthToken.objects.get(user=self.lawyer_user, provider="google")
        self.assertEqual(token.access_token, "google-access-token")
        stored_value = (
            OAuthToken.objects.filter(pk=token.pk)
            .values_list("access_token", flat=True)
            .get()
        )
        self.assertTrue(stored_value.startswith("enc::"))
        self.assertNotIn("google-access-token", stored_value)

        client_user = User.objects.create_user(
            phone_number="+989140000008",
            password="secret",
            first_name="Client",
        )
        client_profile = ClientProfile.objects.create(user=client_user)
        slot_start = timezone.now() + timedelta(hours=1)
        slot_end = slot_start + timedelta(minutes=45)
        slot = OnlineSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=slot_start,
            end_time=slot_end,
        )
        appointment = OnlineAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=client_profile,
            slot=slot,
        )

        result = appointment.confirm(calendar_service=CalendarService())
        self.assertTrue(result.success)
        self.assertTrue(appointment.calendar_event_id)

    @patch("appointments.integrations.views.get_oauth_client")
    def test_manual_refresh_endpoint_updates_token(self, mock_get_client):
        token = OAuthToken.objects.create(
            user=self.lawyer_user,
            provider="google",
            access_token="stale-access",
            refresh_token="static-refresh",
            scope="scope",
            token_type="Bearer",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        client_mock = Mock()
        client_mock.scope = ("https://www.googleapis.com/auth/calendar.events",)
        client_mock.refresh_token.return_value = {
            "access_token": "refreshed-access",
            "expires_in": 7200,
        }
        mock_get_client.return_value = client_mock

        refresh_url = reverse("appointments:calendar-oauth-refresh", args=["google"])
        response = self.api_client.post(refresh_url)
        self.assertEqual(response.status_code, 200)

        token.refresh_from_db()
        self.assertEqual(token.access_token, "refreshed-access")
        self.assertFalse(token.is_expired)

    @patch("appointments.tasks.get_oauth_client")
    def test_refresh_task_updates_expiring_tokens(self, mock_get_client):
        token = OAuthToken.objects.create(
            user=self.lawyer_user,
            provider="google",
            access_token="old-access",
            refresh_token="keep-refresh",
            scope="scope",
            token_type="Bearer",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        client_mock = Mock()
        client_mock.refresh_token.return_value = {
            "access_token": "task-access",
            "expires_in": 1800,
        }
        mock_get_client.return_value = client_mock

        refreshed = refresh_expiring_oauth_tokens()
        self.assertEqual(refreshed, 1)
        token.refresh_from_db()
        self.assertEqual(token.access_token, "task-access")


class OnlineSlotListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.lawyer_user = User.objects.create_user(
            phone_number="+989160000009",
            password="secret",
            first_name="Lawyer",
        )
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        now = timezone.now()
        start_today = now + timedelta(days=1, hours=1)
        end_today = start_today + timedelta(minutes=30)
        self.slot_today = OnlineSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=start_today,
            end_time=end_today,
            price=300000,
        )

        start_tomorrow = now + timedelta(days=2)
        end_tomorrow = start_tomorrow + timedelta(minutes=30)
        self.slot_tomorrow = OnlineSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=start_tomorrow,
            end_time=end_tomorrow,
            price=600000,
        )

        # Past slot should never be returned
        past_start = now - timedelta(days=1)
        OnlineSlot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=past_start,
            end_time=past_start + timedelta(minutes=30),
        )

        other_lawyer = LawyerProfile.objects.create(
            user=User.objects.create_user(
                phone_number="+989170000010",
                password="secret",
                first_name="Other",
            )
        )
        future_start = now + timedelta(days=1)
        OnlineSlot.objects.create(
            lawyer=other_lawyer,
            start_time=future_start,
            end_time=future_start + timedelta(minutes=30),
            price=400000,
        )

        self.url = reverse("appointments:online-slot-list", args=[self.lawyer_profile.pk])

    def test_filter_by_date_returns_matching_slots(self):
        date_str = self.slot_today.start_time.date().isoformat()
        response = self.client.get(self.url, {"date": date_str})

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.slot_today.id)

    def test_filter_by_price_range(self):
        response = self.client.get(self.url, {"price_min": "400000", "price_max": "700000"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.slot_tomorrow.id)

    def test_invalid_date_returns_error(self):
        response = self.client.get(self.url, {"date": "2024-13-40"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.data)

    def test_invalid_price_range_returns_error(self):
        response = self.client.get(self.url, {"price_min": "800000", "price_max": "200000"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("price_range", response.data)
