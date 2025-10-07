import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message
from notifications.utils import send_chat_notification

logger = logging.getLogger("chat")

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close()
            return

        # انتظار دریافت room_id در path یا query
        # من فرض می‌کنم مسیر ws://.../ws/chat/<room_id>/
        self.room_id = self.scope['url_route']['kwargs'].get('room_id')
        if not self.room_id:
            await self.close()
            return

        self.group_name = f"chat_{self.room_id}"

        # Join group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            logger.exception("Error disconnecting from group")

    async def receive(self, text_data=None, bytes_data=None):
        """
        پیامی که از وب‌سوکت میاد باید فرمت JSON مثلا:
        {
            "type": "message",
            "content": "سلام",
            "file_url": null
        }
        """
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.send_json({"error": "unauthenticated"})
            return

        try:
            data = json.loads(text_data)
        except Exception:
            await self.send_json({"error": "invalid_json"})
            return

        msg_type = data.get("type", "message")
        if msg_type == "message":
            content = data.get("content", "").strip()
            file_info = data.get("file")  # optional, handle externally

            # ذخیره پیام در DB
            msg_obj = await self.create_message(self.room_id, user, content, file_info)

            # ارسال پیام به همه‌ی کلاینت‌های گروه
            payload = {
                "type": "chat.message",
                "message": {
                    "id": msg_obj.id,
                    "room": self.room_id,
                    "sender": {"id": user.id, "name": user.get_full_name()},
                    "content": msg_obj.content,
                    "file": msg_obj.file.url if msg_obj.file else None,
                    "created_at": msg_obj.created_at.isoformat(),
                }
            }
            await self.channel_layer.group_send(self.group_name, payload)

            # نوتیف برای دریافت‌کننده (non-blocking)
            try:
                receiver = await self.get_other_user(self.room_id, user)
                if receiver:
                    # send_chat_notification sync function uses DB & SMS; call in thread
                    await self.notify_receiver(user, receiver, msg_obj.content)
            except Exception:
                logger.exception("notify failed")

        elif msg_type == "read":
            # mark read — payload: {"type":"read", "message_ids": [1,2,3]}
            message_ids = data.get("message_ids", [])
            await self.mark_messages_read(message_ids)

    # event handler for group messages
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    # ---------------- DB helpers ----------------
    @database_sync_to_async
    def create_message(self, room_id, sender, content, file_info=None):
        room = ChatRoom.objects.get(pk=room_id)
        # اگر فایلی داری، بهتره فایل را از پیش‌بارگذاری یا url ذخیره کنی. اینجا ساده می‌سازیم:
        m = Message.objects.create(room=room, sender=sender, content=content)
        return m

    @database_sync_to_async
    def get_other_user(self, room_id, user):
        room = ChatRoom.objects.select_related("relation__client__user", "relation__lawyer__user").get(pk=room_id)
        lawyer_user = getattr(room.relation.lawyer, "user", None)
        client_user = getattr(room.relation.client, "user", None)
        if user.id == lawyer_user.id:
            return client_user
        return lawyer_user

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        Message.objects.filter(id__in=message_ids).update(is_read=True)

    @database_sync_to_async
    def notify_receiver(self, sender, receiver, message_text):
        # call notifications.utils -> send_chat_notification (sync)
        send_chat_notification(sender, receiver, message_text)