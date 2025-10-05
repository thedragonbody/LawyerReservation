from django.db import models
from users.models import User

class Notification(models.Model):
    class Status(models.TextChoices):
        UNREAD = 'unread', 'Unread'
        READ = 'read', 'Read'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNREAD)
    link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.title} -> {self.user.email}"