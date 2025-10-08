from rest_framework import serializers
from .models import ChatRoom, Message, MessageReadStatus
from users.serializers import UserSerializer

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    is_read_by_user = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "room", "sender", "sender_name", "content", "file", "is_read", "is_read_by_user", "created_at"]
        read_only_fields = ["id", "sender", "sender_name", "created_at", "is_read", "is_read_by_user"]

    def get_is_read_by_user(self, obj):
        user = self.context.get("request").user
        if not user.is_authenticated:
            return False
        return obj.read_statuses.filter(user=user).exists()


class ChatRoomSerializer(serializers.ModelSerializer):
    lawyer = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ["id", "lawyer", "client", "last_message", "unread_count", "created_at"]

    def get_lawyer(self, obj):
        return UserSerializer(obj.relation.lawyer).data

    def get_client(self, obj):
        return UserSerializer(obj.relation.client).data

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        return MessageSerializer(last, context=self.context).data if last else None

    def get_unread_count(self, obj):
        user = self.context["request"].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()