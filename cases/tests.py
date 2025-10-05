from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User, LawyerProfile, ClientProfile
from .models import Case, CaseComment

class CaseAPITest(TestCase):
    def setUp(self):
        # ایجاد کاربر وکیل
        self.lawyer_user = User.objects.create_user(email="lawyer@example.com", phone_number="1111111111", first_name="Lawyer", last_name="One", password="password123")
        self.lawyer_profile = LawyerProfile.objects.create(user=self.lawyer_user)

        # ایجاد کاربر کلاینت
        self.client_user = User.objects.create_user(email="client@example.com", phone_number="2222222222", first_name="Client", last_name="One", password="password123")
        self.client_profile = ClientProfile.objects.create(user=self.client_user, national_id="1234567890")

        # APIClientها
        self.client_api = APIClient()
        self.lawyer_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)
        self.lawyer_api.force_authenticate(user=self.lawyer_user)

        # ایجاد پرونده توسط وکیل
        self.case = Case.objects.create(
            lawyer=self.lawyer_profile,
            title="Test Case",
            description="Test description",
            is_public=True
        )

    # ----------------------------
    # لیست پرونده‌ها برای همه
    # ----------------------------
    def test_anyone_can_list_cases(self):
        url = reverse("case-list-create")
        response = self.client_api.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    # ----------------------------
    # کلاینت نمی‌تواند پرونده ایجاد کند
    # ----------------------------
    def test_client_cannot_create_case(self):
        url = reverse("case-list-create")
        data = {"title": "Client Case", "description": "Should fail"}
        response = self.client_api.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ----------------------------
    # وکیل می‌تواند پرونده ایجاد کند
    # ----------------------------
    def test_lawyer_can_create_case(self):
        url = reverse("case-list-create")
        data = {"title": "Lawyer Case", "description": "Should succeed"}
        response = self.lawyer_api.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], "Lawyer Case")

    # ----------------------------
    # کلاینت می‌تواند کامنت بدهد
    # ----------------------------
    def test_client_can_add_comment(self):
        url = reverse("case-comment-create", args=[self.case.id])
        data = {"content": "This is a comment"}
        response = self.client_api.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], "This is a comment")

    # ----------------------------
    # کلاینت فقط می‌تواند کامنت خودش را حذف کند
    # ----------------------------
    def test_client_can_delete_own_comment(self):
        comment = CaseComment.objects.create(case=self.case, user=self.client_user, content="Own comment")
        url = reverse("comment-detail", args=[comment.id])
        response = self.client_api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_client_cannot_delete_others_comment(self):
        comment = CaseComment.objects.create(case=self.case, user=self.lawyer_user, content="Lawyer comment")
        url = reverse("comment-detail", args=[comment.id])
        response = self.client_api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ----------------------------
    # وکیل می‌تواند هر کامنت روی پرونده خودش را حذف کند
    # ----------------------------
    def test_lawyer_can_delete_any_comment_in_own_case(self):
        comment = CaseComment.objects.create(case=self.case, user=self.client_user, content="Client comment")
        url = reverse("comment-detail", args=[comment.id])
        response = self.lawyer_api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)