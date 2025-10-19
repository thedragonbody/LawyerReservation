from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from users.models import User
from chat.models import Message, ChatRoom
from notifications.utils import send_chat_notification, send_push_notification

class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        ارسال پیام به کاربر دیگر
        """
        recipient_id = request.data.get("recipient_id")
        text = request.data.get("text")

        if not recipient_id or not text:
            return Response({"error": "recipient_id و text الزامی است"}, status=400)

        recipient = get_object_or_404(User, id=recipient_id)

        # پیدا کردن یا ایجاد ChatRoom
        room, created = ChatRoom.objects.get_or_create_between_users(
            request.user, recipient
        )

        message = Message.objects.create(
            room=room,
            sender=request.user,
            content=text
        )

        # ارسال نوتیفیکیشن
        send_chat_notification(recipient, f"پیام جدید از {request.user.email}: {text}")
        send_push_notification(recipient, "پیام جدید", text)

        return Response({"success": True, "message_id": message.id})


class GetMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id, *args, **kwargs):
        """
        دریافت پیام‌ها برای یک ChatRoom
        """
        room = get_object_or_404(ChatRoom, id=room_id)
        if request.user not in room.users.all():
            return Response({"error": "دسترسی غیرمجاز"}, status=403)

        messages = room.messages.order_by("created_at")
        data = [
            {
                "id": msg.id,
                "sender": msg.sender.email,
                "content": msg.content,
                "created_at": msg.created_at
            }
            for msg in messages
        ]
        return Response(data)


class TypingIndicatorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id, *args, **kwargs):
        """
        نشانگر تایپ کردن
        """
        room = get_object_or_404(ChatRoom, id=room_id)
        if request.user not in room.users.all():
            return Response({"error": "دسترسی غیرمجاز"}, status=403)

        # می‌توانید اینجا WebSocket یا Celery برای اطلاع‌رسانی زمان واقعی استفاده کنید
        return Response({"success": True, "status": "typing"})