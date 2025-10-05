from rest_framework.test import APITestCase
from users.models import User
from notifications.models import Notification

class NotificationAPITestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        # کاربر با نوتیفیکیشن
        cls.user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            phone_number="+989123456789"
        )
        for i in range(4):
            Notification.objects.create(
                user=cls.user,
                title=f"Notification {i+1}",
                message="Test message"
            )

    def test_notification_list_empty(self):
        # یک کاربر کاملاً جدید
        new_user = User.objects.create_user(
            email="empty@example.com",
            password="password123",
            phone_number="+989123456780"
        )
        self.client.force_authenticate(user=new_user)
        response = self.client.get('/notifications/')
        print("Response data:", response.data)  # برای دیباگ
        self.assertEqual(len(response.data), 0)