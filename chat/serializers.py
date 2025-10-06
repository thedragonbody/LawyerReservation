from rest_framework import serializers
from .models import Conversation, Message
from users.serializers import UserSerializer  # چون از User سفارشی استفاده می‌کنی

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'text', 'file', 'is_read', 'timestamp']

class ConversationSerializer(serializers.ModelSerializer):
    lawyer = UserSerializer(read_only=True)
    client = UserSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'lawyer', 'client', 'messages', 'created_at']