from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import PasswordResetCode

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'is_active']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """اضافه کردن claimهای نقش"""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_client'] = hasattr(user, 'client_profile')
        token['is_lawyer'] = hasattr(user, 'lawyer_profile')
        return token


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        try:
            PasswordResetCode.verify_code(
                attrs['phone_number'],
                attrs['code'],
                purpose='signup'
            )
        except ValueError as e:
            raise serializers.ValidationError({'detail': str(e)})
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

    def validate(self, attrs):
        # امنیتی: پیام عمومی، حتی اگر کاربر وجود نداشته باشد
        phone = attrs['phone_number']
        PasswordResetCode.generate_code(phone, 'reset')
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, attrs):
        try:
            PasswordResetCode.verify_code(
                attrs['phone_number'],
                attrs['code'],
                purpose='reset'
            )
        except ValueError as e:
            raise serializers.ValidationError({'detail': str(e)})
        return attrs

    def save(self):
        user = User.objects.filter(phone_number=self.validated_data['phone_number']).first()
        if not user:
            raise serializers.ValidationError("کاربر یافت نشد.")
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user