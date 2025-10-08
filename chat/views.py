from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from common.models import LawyerClientRelation
from .models import ChatRoom, Message, MessageReadStatus
from notifications.utils import send_chat_notification, send_push_notification
from django.utils import timezone

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

        # ایجاد read status اولیه (فرستنده خودش خوانده)
        MessageReadStatus.objects.create(message=msg, user=request.user, read_at=timezone.now())

        # ارسال نوتیفیکیشن داخلی و push به گیرنده
        receiver = relation.client.user if request.user != relation.client.user else relation.lawyer.user
        send_chat_notification(receiver, f"پیام جدید از {request.user.get_full_name()}", msg.content)
        send_push_notification(receiver, title=f"پیام جدید از {request.user.get_full_name()}", message=msg.content)

        return Response({"message": "ارسال شد", "id": msg.id}, status=status.HTTP_201_CREATED)


class GetMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lawyer_id, client_id):
        try:
            relation = LawyerClientRelation.objects.get(lawyer_id=lawyer_id, client_id=client_id)
            room = relation.chat_room
        except (LawyerClientRelation.DoesNotExist, ChatRoom.DoesNotExist):
            return Response({"detail": "چت موجود نیست"}, status=404)

        messages = room.messages.order_by("created_at").values(
            "id", "sender_id", "content", "file", "is_read", "created_at"
        )

        # به‌روزرسانی read status برای کاربر فعلی
        unread_messages = room.messages.filter(is_read=False).exclude(sender=request.user)
        for msg in unread_messages:
            MessageReadStatus.objects.get_or_create(message=msg, user=request.user, defaults={"read_at": timezone.now()})
            msg.is_read = True
            msg.save(update_fields=["is_read"])

        return Response({"messages": list(messages)}, status=200)


class TypingIndicatorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        اعلام تایپ کردن به طرف مقابل
        """
        lawyer_id = request.data.get("lawyer_id")
        client_id = request.data.get("client_id")

        if not all([lawyer_id, client_id]):
            return Response({"detail": "مقادیر لازم ارسال نشده"}, status=400)

        try:
            relation = LawyerClientRelation.objects.get(lawyer_id=lawyer_id, client_id=client_id)
        except LawyerClientRelation.DoesNotExist:
            return Response({"detail": "ارتباط بین این کاربرها وجود ندارد"}, status=404)

        receiver = relation.client.user if request.user != relation.client.user else relation.lawyer.user

        # ارسال نوتیف تایپ به گیرنده (Push یا داخلی)
        send_push_notification(
            receiver,
            title=f"{request.user.get_full_name()} در حال تایپ است",
            message=""
        )

        return Response({"message": "تایپ کردن به طرف مقابل اعلام شد"}, status=200)