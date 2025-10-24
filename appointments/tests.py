from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from appointments.models import OnlineAppointment, OnlineSlot
from common.choices import AppointmentStatus
from appointments.integrations import CalendarService
from client_profile.models import ClientProfile
from lawyer_profile.models import LawyerProfile
from users.models import OAuthToken, User


class OnlineAppointmentCalendarSyncTests(TestCase):
    def setUp(self):
        self.lawyer_user = User.objects.create_user(phone_number="09120000001", password="pass", is_active=True)
        self.client_user = User.objects.create_user(phone_number="09120000002", password="pass", is_active=True)
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.client_user)

    def create_slot(self, hours_ahead=48):
        start = timezone.now() + timedelta(hours=hours_ahead)
        end = start + timedelta(minutes=45)
        return OnlineSlot.objects.create(lawyer=self.lawyer_profile, start_time=start, end_time=end)

    def create_appointment(self, slot=None):
        slot = slot or self.create_slot()
        return OnlineAppointment.objects.create(lawyer=self.lawyer_profile, client=self.client_profile, slot=slot)

    def provide_token(self, expires_in_hours=1):
        return OAuthToken.objects.update_or_create(
            user=self.lawyer_user,
            provider="google",
            defaults={
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_at": timezone.now() + timedelta(hours=expires_in_hours),
            },
        )

    def test_confirm_sync_success_with_valid_token(self):
        self.provide_token()
        appointment = self.create_appointment()

        result = appointment.confirm()

        appointment.refresh_from_db()
        appointment.slot.refresh_from_db()
        self.assertTrue(result.success)
        self.assertIsNotNone(appointment.calendar_event_id)
        self.assertEqual(appointment.status, AppointmentStatus.CONFIRMED)
        self.assertTrue(appointment.slot.is_booked)

    def test_confirm_sync_returns_warning_without_token(self):
        appointment = self.create_appointment()

        result = appointment.confirm()

        appointment.refresh_from_db()
        self.assertFalse(result.success)
        self.assertIsNone(appointment.calendar_event_id)
        self.assertEqual(appointment.status, AppointmentStatus.CONFIRMED)
        self.assertIn("توکن", result.message)

    def test_cancel_clears_event_when_sync_succeeds(self):
        self.provide_token()
        appointment = self.create_appointment()
        appointment.confirm()
        appointment.refresh_from_db()
        self.assertIsNotNone(appointment.calendar_event_id)

        result = appointment.cancel(user=self.client_user, calendar_service=CalendarService())

        appointment.refresh_from_db()
        appointment.slot.refresh_from_db()
        self.assertTrue(result.success)
        self.assertIsNone(appointment.calendar_event_id)
        self.assertEqual(appointment.status, AppointmentStatus.CANCELLED)
        self.assertFalse(appointment.slot.is_booked)

    def test_cancel_returns_warning_when_token_missing(self):
        self.provide_token()
        appointment = self.create_appointment()
        appointment.confirm()
        appointment.refresh_from_db()
        # حذف توکن برای شبیه‌سازی خطا
        OAuthToken.objects.filter(user=self.lawyer_user, provider="google").delete()

        result = appointment.cancel(user=self.client_user)

        appointment.refresh_from_db()
        self.assertFalse(result.success)
        self.assertEqual(appointment.status, AppointmentStatus.CANCELLED)
        self.assertIn("توکن", result.message)

    def test_create_view_includes_warning_when_calendar_sync_fails(self):
        slot = self.create_slot()
        response = self.api_client.post(
            reverse("online-appointment-create"),
            {"slot": slot.id, "description": "جلسه"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("calendar_sync_warning", response.data)

    def test_reschedule_view_returns_warning_if_calendar_update_fails(self):
        slot = self.create_slot()
        appointment = self.create_appointment(slot=slot)
        # تایید بدون توکن => sync failure on creation but رزرو تایید می‌شود
        appointment.confirm()
        new_slot = self.create_slot(hours_ahead=72)

        response = self.api_client.post(
            reverse("online-appointment-reschedule", args=[appointment.pk]),
            {"new_slot_id": new_slot.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("calendar_sync_warning", response.data)
