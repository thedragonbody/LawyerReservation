import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close()
            return

        self.group_name = f"notifications_{user.id}"
        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        except Exception as e:
            logger.exception("Failed to add user to group: %s", e)
            await self.close()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            logger.exception("Failed to remove user from group")

    async def send_notification(self, event):
        try:
            await self.send(text_data=json.dumps(event.get("message", {})))
        except Exception:
            logger.exception("Failed to send message to WebSocket client")