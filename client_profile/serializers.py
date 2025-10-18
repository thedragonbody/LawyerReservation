from rest_framework import serializers
from .models import ClientProfile

class ClientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientProfile
        fields = ['user', 'national_id', 'avatar', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']