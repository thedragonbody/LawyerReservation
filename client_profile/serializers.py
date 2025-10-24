from rest_framework import serializers
from .models import ClientProfile, Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'name', 'ip_address', 'user_agent', 'last_seen', 'created_at', 'revoked']
        read_only_fields = ['id', 'last_seen', 'created_at', 'revoked']


class ClientProfileSerializer(serializers.ModelSerializer):
    favorites = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    devices = DeviceSerializer(many=True, read_only=True)

    class Meta:
        model = ClientProfile
        fields = [
            'user',
            'national_id',
            'avatar',
            'is_phone_verified',
            'favorites',
            'devices',
            'last_login_ip',
            'last_login_user_agent',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['is_phone_verified', 'favorites', 'devices', 'last_login_ip', 'last_login_user_agent']

class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6)
