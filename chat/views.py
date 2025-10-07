from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from common.models import LawyerClientRelation
from .models import ChatRoom, Message
from notifications.utils import send_chat_notification

class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        lawyer_id = request.data.get("lawyer_id")
        client_id = request.data.get("client_id")
        content = request.data.get("content")

        if not all([lawyer_id, client_id, content]):
            return Response({"detail": "مقادیر لازم ارسال نشده"}, status=400)

        try:
            relation = LawyerClientRelation.objects.get(lawyer_id=lawyer_id, client_id=client_id)
        except LawyerClientRelation.DoesNotExist:
            return Response({"detail": "ارتباط بین این کاربرها وجود ندارد"}, status=404)

        room, _ = ChatRoom.objects.get_or_create(relation=relation)

        msg = Message.objects.create(room=room, sender=request.user, content=content)

        # ارسال نوتیفیکیشن به گیرنده
        receiver = relation.client.user if request.user != relation.client.user else relation.lawyer.user
        send_chat_notification(receiver, f"پیام جدید از {request.user.get_full_name()}", msg.content)

        return Response({"message": "ارسال شد", "id": msg.id}, status=status.HTTP_201_CREATED)


class GetMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lawyer_id, client_id):
        try:
            relation = LawyerClientRelation.objects.get(lawyer_id=lawyer_id, client_id=client_id)
            room = relation.chat_room
        except (LawyerClientRelation.DoesNotExist, ChatRoom.DoesNotExist):
            return Response({"detail": "چت موجود نیست"}, status=404)

        messages = room.messages.order_by("created_at").values("id", "sender_id", "content", "is_read", "created_at")
        return Response({"messages": list(messages)}, status=200)