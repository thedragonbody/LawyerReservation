from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework import status

from users.models import User
from chat.models import Message, ChatRoom
from chat.tasks import send_chat_notifications_task # 💡 NEW: Import Celery task

class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        room_id = request.data.get("room_id")
        text = request.data.get("text")
        
        if not room_id or not text:
            return Response({"error": "room_id و text الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

        room = get_object_or_404(ChatRoom, id=room_id)
        
        user_ids = [room.relation.lawyer.user_id, room.relation.client.user_id]
        if request.user.id not in user_ids:
             return Response({"error": "شما عضوی از این اتاق چت نیستید"}, status=status.HTTP_403_FORBIDDEN)
        
        # تعیین گیرنده
        if request.user.id == room.relation.lawyer.user_id:
            recipient = room.relation.client.user
        else:
            recipient = room.relation.lawyer.user

        message = Message.objects.create(
            room=room,
            sender=request.user,
            content=text
        )

        # 🚀 NEW: ارسال نوتیفیکیشن به صورت غیرهمزمان
        send_chat_notifications_task.delay(request.user.id, recipient.id, text)

        return Response({"success": True, "message_id": message.id}, status=status.HTTP_201_CREATED)


class GetMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id, *args, **kwargs):
        room = get_object_or_404(ChatRoom, id=room_id)
        user_ids = [room.relation.lawyer.user_id, room.relation.client.user_id]
        if request.user.id not in user_ids:
             return Response({"error": "دسترسی غیرمجاز"}, status=status.HTTP_403_FORBIDDEN)

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
        room = get_object_or_404(ChatRoom, id=room_id)
        user_ids = [room.relation.lawyer.user_id, room.relation.client.user_id]
        if request.user.id not in user_ids:
             return Response({"error": "دسترسی غیرمجاز"}, status=status.HTTP_403_FORBIDDEN)

        # 💡 NOTE: این ویو صرفاً Placeholder است و برای عملکرد Real-time به Channel Layer نیاز دارد.
        return Response({"success": True, "status": "typing"})