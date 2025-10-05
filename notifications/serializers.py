from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'status', 'link', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']