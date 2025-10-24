from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import OAuthToken, PasswordResetCode
from client_profile.models import ClientProfile

User = get_user_model()


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

    def validate_phone_number(self, value):
        # در صورت نیاز فرمت شماره را اینجا ولیدیت کن
        return value


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        try:
            PasswordResetCode.verify_code(
                attrs['phone_number'],
                attrs['code'],
                purpose='login'  # برای Passwordless login از purpose = 'login' استفاده می‌کنیم
            )
        except ValueError as e:
            raise serializers.ValidationError({'detail': str(e)})
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    serializer خواندن اطلاعات کاربر (بدون password چون Passwordless).
    """
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'is_active', 'date_joined']
        read_only_fields = ['id', 'is_active', 'date_joined']



class ResendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)


class OAuthTokenSerializer(serializers.ModelSerializer):
    expires_in = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = OAuthToken
        fields = [
            'provider',
            'access_token',
            'refresh_token',
            'scope',
            'token_type',
            'expires_at',
            'expires_in',
        ]
        read_only_fields = ['provider']

    def validate(self, attrs):
        expires_at = attrs.get('expires_at')
        expires_in = attrs.get('expires_in')
        if expires_at and expires_in:
            raise serializers.ValidationError({'expires_at': 'یکی از فیلدهای expires_at یا expires_in را ارسال کنید.'})
        return attrs

    def create(self, validated_data):
        raise NotImplementedError('Use update_or_create via the view')

    def update(self, instance, validated_data):
        raise NotImplementedError('Use update_or_create via the view')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['provider'] = instance.provider
        data['is_expired'] = instance.is_expired
        return data
    
    
