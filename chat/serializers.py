from rest_framework import serializers
from .models import ChatRoom, Message
from users.serializers import UserSerializer

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "room", "sender", "content", "file", "is_read", "created_at"]
        read_only_fields = ["id", "sender", "created_at", "is_read"]

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
        return MessageSerializer(last).data if last else None

    def get_unread_count(self, obj):
        user = self.context["request"].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()