import os
from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.urls import reverse

from rest_framework.test import APIClient, APIRequestFactory

from appointments.integrations import CalendarService, CalendarSyncError
from appointments.models import (
    OnlineAppointment,
    OnlineSlot,
    OnsiteAppointment,
    OnsiteSlot,
)
from appointments.serializers import OnlineAppointmentSerializer
from appointments.services.reminders import dispatch_upcoming_reminders
from appointments.tasks import refresh_expiring_oauth_tokens, send_appointment_reminders_task
from appointments.views import OnlineAppointmentListView
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
        with self.assertLogs("appointments.services.reminders", level="INFO") as captured:
            result = send_appointment_reminders_task()

        self.assertEqual(result["processed_appointments"], 1)
        self.appointment.refresh_from_db()
        self.assertTrue(self.appointment.is_reminder_sent)

        # Two SMS + two push notifications (client + lawyer)
        self.assertEqual(result["notifications"]["sms"]["sent"], 2)
        self.assertEqual(result["notifications"]["push"]["sent"], 2)
        self.assertEqual(result["notifications"]["sms"]["failed"], 0)
        self.assertEqual(result["notifications"]["push"]["failed"], 0)
        self.assertTrue(any("Sent push reminder" in message for message in captured.output))

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

        result = send_appointment_reminders_task()

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

        self.assertEqual(result["notifications"]["sms"]["sent"], 1)
        self.assertEqual(result["notifications"]["push"]["sent"], 1)
        self.assertEqual(result["notifications"]["sms"]["failed"], 0)
        self.assertEqual(result["notifications"]["push"]["failed"], 0)

    @patch("appointments.services.reminders.send_sms")
    @patch("appointments.services.reminders.Notification.send")
    def test_send_appointment_reminders_logs_failures(self, mock_notification_send, mock_send_sms):
        mock_notification_send.side_effect = [Exception("push down"), None]
        mock_send_sms.side_effect = [Exception("sms down"), None]

        with self.assertLogs("appointments.services.reminders", level="ERROR") as captured:
            result = send_appointment_reminders_task()

        self.assertEqual(result["notifications"]["push"]["failed"], 1)
        self.assertEqual(result["notifications"]["sms"]["failed"], 1)
        self.assertEqual(len(result["errors"]), 2)
        self.assertTrue(any("Failed to send push reminder" in message for message in captured.output))

    def test_dispatch_upcoming_reminders_uses_settings_window(self):
        with patch(
            "appointments.services.reminders._get_upcoming_online_appointments"
        ) as mock_get:
            mock_get.return_value = []
            with self.settings(APPOINTMENT_REMINDER_WINDOW=timedelta(minutes=45)):
                result = dispatch_upcoming_reminders()

        mock_get.assert_called_once()
        self.assertEqual(
            mock_get.call_args.kwargs["window"], timedelta(minutes=45)
        )
        self.assertEqual(result["processed_appointments"], 0)

    def test_dispatch_upcoming_reminders_falls_back_to_env_window(self):
        with patch(
            "appointments.services.reminders._get_upcoming_online_appointments"
        ) as mock_get, patch.dict(os.environ, {"APPOINTMENT_REMINDER_WINDOW": "120"}):
            mock_get.return_value = []
            with self.settings(APPOINTMENT_REMINDER_WINDOW=None):
                dispatch_upcoming_reminders()

        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs["window"], timedelta(minutes=120))


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

        appointment = OnsiteAppointment.objects.create(
            lawyer=self.lawyer_profile,
            client=self.client_profile,
            slot=self.slot,
        )

        link = create_meeting_link(appointment, provider="google")

        mock_calendar_service.assert_called_once_with(provider="google")
        mock_instance.create_event.assert_called_once_with(appointment)
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
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT access_token FROM users_oauthtoken WHERE id = %s", [token.pk]
            )
            raw_value = cursor.fetchone()[0]

        self.assertTrue(raw_value.startswith("enc::"))
        self.assertNotIn("google-access-token", raw_value)

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


class OnlineAppointmentListViewTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            phone_number="+989150000009",
            password="secret",
            first_name="Client",
            last_name="Tester",
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
class OnlineAppointmentSerializerTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            phone_number="+989100000010",
            password="secret",
            first_name="Client",
            last_name="User",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.lawyer_user = User.objects.create_user(
            phone_number="+989150000010",
            password="secret",
            first_name="Lawyer",
            last_name="Expert",
            phone_number="+989100000011",
            password="secret",
            first_name="Lawyer",
            last_name="Person",
        )
        self.lawyer_profile = LawyerProfile.objects.create(
            user=self.lawyer_user,
            expertise="Family Law",
            specialization="Divorce",
            status="online",
        )

        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.client_user)

        base_time = timezone.now() + timedelta(days=1)
        for index in range(3):
            start_time = base_time + timedelta(hours=index)
            end_time = start_time + timedelta(minutes=30)
            slot = OnlineSlot.objects.create(
                lawyer=self.lawyer_profile,
                start_time=start_time,
                end_time=end_time,
            experience_years=5,
            status="online",
        )

        slot_start = timezone.now() + timedelta(days=1)
        slot_end = slot_start + timedelta(minutes=45)
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

    def test_serializer_includes_slot_and_lawyer_metadata(self):
        serializer = OnlineAppointmentSerializer(instance=self.appointment)
        data = serializer.data

        self.assertIn('slot_start_time', data)
        self.assertIn('slot_end_time', data)
        self.assertIn('lawyer_summary', data)

        start_value = parse_datetime(data['slot_start_time'])
        end_value = parse_datetime(data['slot_end_time'])
        self.assertEqual(start_value, self.slot.start_time)
        self.assertEqual(end_value, self.slot.end_time)

        summary = data['lawyer_summary']
        self.assertIsInstance(summary, dict)
        self.assertEqual(summary['id'], self.lawyer_profile.id)
        self.assertEqual(summary['full_name'], self.lawyer_user.get_full_name())
        self.assertEqual(summary['expertise'], self.lawyer_profile.expertise)
        self.assertEqual(summary['specialization'], self.lawyer_profile.specialization)


class OnlineAppointmentListViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.client_user = User.objects.create_user(
            phone_number="+989100000020",
            password="secret",
            first_name="Client",
            last_name="Viewer",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.lawyer_user = User.objects.create_user(
            phone_number="+989100000021",
            password="secret",
            first_name="Lawyer",
            last_name="Viewer",
        )
        self.lawyer_profile = LawyerProfile.objects.create(
            user=self.lawyer_user,
            expertise="Civil",
        )

        for index in range(3):
            slot_start = timezone.now() + timedelta(days=1, hours=index)
            slot_end = slot_start + timedelta(minutes=30)
            slot = OnlineSlot.objects.create(
                lawyer=self.lawyer_profile,
                start_time=slot_start,
                end_time=slot_end,
            )
            OnlineAppointment.objects.create(
                lawyer=self.lawyer_profile,
                client=self.client_profile,
                slot=slot,
                status=AppointmentStatus.CONFIRMED,
            )

    def test_list_view_includes_slot_and_lawyer_metadata(self):
        url = reverse("appointments:online-appointment-list")
        response = self.api_client.get(url)

        self.assertEqual(response.status_code, 200)

        expected_count = OnlineAppointment.objects.filter(
            client=self.client_profile
        ).count()

        data = response.data
        if isinstance(data, dict) and "results" in data:
            data = data["results"]

        self.assertEqual(len(data), expected_count)

        for item in data:
            self.assertIn("slot_start", item)
            self.assertIn("slot_end", item)
            self.assertIn("lawyer_summary", item)

            summary = item["lawyer_summary"]
            self.assertIsInstance(summary, dict)
            self.assertEqual(summary["id"], self.lawyer_profile.id)
            self.assertEqual(summary["name"], self.lawyer_user.get_full_name())
            self.assertEqual(summary["status"], self.lawyer_profile.status)
            self.assertEqual(summary["expertise"], self.lawyer_profile.expertise)
            self.assertEqual(summary["specialization"], self.lawyer_profile.specialization)

    def test_list_view_uses_select_related(self):
        url = reverse("appointments:online-appointment-list")

        with self.assertNumQueries(2):
            response = self.api_client.get(url)

        self.assertEqual(response.status_code, 200)

        data = response.data
        if isinstance(data, dict) and "results" in data:
            data = data["results"]

        self.assertTrue(data)
            )

    def test_queryset_uses_select_related_for_lawyer_and_slot(self):
        view = OnlineAppointmentListView()
        request = self.factory.get('/appointments/')
        request.user = self.client_user
        view.request = request

        queryset = view.get_queryset()

        with self.assertNumQueries(1):
            data = OnlineAppointmentSerializer(queryset, many=True).data

        self.assertEqual(len(data), 3)
