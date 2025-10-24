from django.test import TestCase

from users.models import User
from .models import LawyerProfile


class LawyerProfileFullProfileTests(TestCase):
    def test_full_profile_includes_region_and_office_details(self):
        user = User.objects.create_user(
            phone_number="09123456789",
            password="secure-password",
            first_name="Ali",
            last_name="Rezaei",
        )

        profile = LawyerProfile.objects.create(
            user=user,
            expertise="حقوق مدنی",
            specialization="قراردادها",
            degree="LLB",
            experience_years=7,
            status=LawyerProfile.STATUS_CHOICES[0][0],
            license_number="LIC-001",
            city="تهران",
            region="منطقه 1",
            office_address="تهران، خیابان ولیعصر",
        )

        full_profile = profile.full_profile()

        self.assertEqual(full_profile["region"], "منطقه 1")
        self.assertEqual(full_profile["city"], "تهران")
        self.assertEqual(full_profile["name"], user.get_full_name())
        self.assertEqual(full_profile["office"]["address"], "تهران، خیابان ولیعصر")
        self.assertIn("map_url", full_profile["office"])
        self.assertIsNone(full_profile["avatar"])
