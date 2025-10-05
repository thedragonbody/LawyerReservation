from rest_framework.test import APITestCase
from rest_framework import status
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from users.models import User, ClientProfile, LawyerProfile


class UserAuthTestCase(APITestCase):

    def setUp(self):
        self.user_data = {
            'email': 'allanlondon19452122@gmail.com',
            'phone_number': '09123456789',
            'first_name': 'Allan',
            'last_name': 'London',
            'password': 'StrongPass123'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.client.force_authenticate(user=self.user)

    # ================= Register =================
    def test_register_user(self):
        data = {
            'email': 'newuser123@example.com',
            'phone_number': '09111222333',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'StrongPass123'
        }
        response = self.client.post('/users/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(email=data['email']).count(), 1)

    # ================= Login JWT =================
    def test_login_user(self):
        self.client.logout()
        response = self.client.post('/users/login/', {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    # ================= Change Password =================
    def test_change_password(self):
        url = '/users/change-password/'
        data = {
            'old_password': self.user_data['password'],
            'new_password': 'NewStrongPass456'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass456'))

    # ================= Client Profile =================
    def test_client_profile(self):
        response = self.client.get('/users/profile/client/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.put('/users/profile/client/', {'national_id': '1234567890'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ClientProfile.objects.get(user=self.user).national_id, '1234567890')

    # ================= Lawyer Profile =================
    def test_lawyer_profile(self):
        response = self.client.get('/users/profile/lawyer/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = {'expertise': 'Criminal Law', 'degree': 'LLB', 'experience_years': 5}
        response = self.client.put('/users/profile/lawyer/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lawyer = LawyerProfile.objects.get(user=self.user)
        self.assertEqual(lawyer.expertise, 'Criminal Law')
        self.assertEqual(lawyer.degree, 'LLB')
        self.assertEqual(lawyer.experience_years, 5)


class PasswordResetTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="allanlondon19452122@gmail.com",
            phone_number="09123456789",
            password="OldPass123"
        )
        self.request_url = "/users/password-reset/"
        self.confirm_url = "/users/password-reset-confirm/"

    def test_request_password_reset(self):
        response = self.client.post(self.request_url, {"email": self.user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("password reset", mail.outbox[0].subject.lower())

    def test_confirm_password_reset(self):
        token_generator = PasswordResetTokenGenerator()
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = token_generator.make_token(self.user)

        data = {"uidb64": uidb64, "token": token, "new_password": "NewSecurePass789"}
        response = self.client.post(self.confirm_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        login = self.client.post("/users/login/", {"email": self.user.email, "password": "NewSecurePass789"})
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_confirm_password_reset_invalid_token(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        data = {"uidb64": uidb64, "token": "invalidtoken", "new_password": "AnyPass123"}
        response = self.client.post(self.confirm_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)