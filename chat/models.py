from django.db import models
from django.conf import settings
from common.models import LawyerClientRelation  # طبق ساختار پیشنهادی قبلی

# ------------------- Chat Room -------------------
class ChatRoom(models.Model):
    relation = models.OneToOneField(
        LawyerClientRelation,
        on_delete=models.CASCADE,
        related_name="chat_room"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ChatRoom {self.id} – {self.relation}"


# ------------------- Message -------------------
class Message(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="chat_files/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender} @ {self.created_at}: {self.content[:30]}"


# ------------------- Message Read Status -------------------
class MessageReadStatus(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="read_statuses"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("message", "user")
        ordering = ["read_at"]

    def __str__(self):
        return f"{self.user} read {self.message.id} at {self.read_at}"