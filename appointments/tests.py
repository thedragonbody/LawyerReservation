from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User, ClientProfile, LawyerProfile
from appointments.models import Slot, Appointment
from datetime import timedelta
from django.utils import timezone


class AppointmentTestCase(APITestCase):
    def setUp(self):
        self.lawyer_user = User.objects.create_user(email="lawyer@test.com", password="pass", phone_number="0912000000")
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        self.client_user = User.objects.create_user(email="client@test.com", password="pass", phone_number="0912000001")
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.slot = Slot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1)
        )

        self.appointment = Appointment.objects.create(
            client=self.client_profile,
            lawyer=self.lawyer_profile,
            slot=self.slot,
            status=Appointment.Status.PENDING
        )

    def test_list_slots(self):
        self.client.force_authenticate(user=self.lawyer_user)
        url = reverse("slot-list-create")
        response = self.client.get(url)
        # ✅ چون paginate می‌شود
        self.assertEqual(len(response.data["results"]), 1)

    def test_permission_owner_only(self):
        other_user = User.objects.create_user(email="other@test.com", password="pass", phone_number="0912000002")
        self.client.force_authenticate(user=other_user)
        url = reverse("appointment-detail", args=[self.appointment.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class AppointmentExtraTestCase(APITestCase):
    def setUp(self):
        self.lawyer_user = User.objects.create_user(email="lawyer2@test.com", password="pass", phone_number="0912000003")
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        self.client_user = User.objects.create_user(email="client2@test.com", password="pass", phone_number="0912000004")
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.slot = Slot.objects.create(
            lawyer=self.lawyer_profile,
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=1)
        )

        self.appointment = Appointment.objects.create(
            client=self.client_profile,
            lawyer=self.lawyer_profile,
            slot=self.slot,
            status=Appointment.Status.PENDING
        )

    def test_lawyer_can_confirm_appointment(self):
        self.client.force_authenticate(user=self.lawyer_user)
        url = reverse("appointment-confirm", args=[self.appointment.id])
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_client_cannot_confirm_appointment(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse("appointment-confirm", args=[self.appointment.id])
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pagination_in_appointment_list(self):
        for i in range(15):
            Slot.objects.create(
                lawyer=self.lawyer_profile,
                start_time=timezone.now() + timedelta(days=3+i),
                end_time=timezone.now() + timedelta(days=3+i, hours=1)
            )
        self.client.force_authenticate(user=self.lawyer_user)
        url = reverse("appointment-list")
        response = self.client.get(url)
        self.assertIn("results", response.data)
        self.assertLessEqual(len(response.data["results"]), 10)