from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import PasswordResetCode
from client_profile.models import ClientProfile
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers

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
    
    