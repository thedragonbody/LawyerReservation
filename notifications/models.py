from django.db import models
from django.utils import timezone
from users.models import User

class Notification(models.Model):
    """
    ذخیره و ارسال نوتیفیکیشن برای کاربران.
    """
    class Type(models.TextChoices):
        APPOINTMENT_CONFIRMED = "appointment_confirmed", "Appointment Confirmed"
        APPOINTMENT_REMINDER = "appointment_reminder", "Appointment Reminder"
        PAYMENT_SUCCESS = "payment_success", "Payment Success"
        INPERSON_PAYMENT_SUCCESS = "inperson_payment_success", "In-person Payment Success"
        INPERSON_PAYMENT_REFUNDED = "inperson_payment_refunded", "In-person Payment Refunded"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=50, choices=Type.choices)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"

    @staticmethod
    def send(user, title, message, type_):
        """
        ایجاد نوتیفیکیشن در دیتابیس (و در آینده push)
        """
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            type=type_,
        )