from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, PasswordResetCode
from django.db import transaction
from django.contrib.auth.hashers import make_password

# ----------------------------
# User Serializer (با OTP)
# ----------------------------
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password'],
            is_active=False  # کاربر در ابتدا غیرفعال است
        )
        return user

# ----------------------------
# Change Password Serializer
# ----------------------------
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])


# ----------------------------
# Logout Serializer
# ----------------------------
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except Exception:
            self.fail('bad_token')


# ----------------------------
# Custom JWT Serializer
# ----------------------------
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_client'] = hasattr(user, 'client')
        token['is_lawyer'] = hasattr(user, 'lawyer')
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            "id": self.user.id,
            "phone_number": self.user.phone_number,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }
        return data


# ----------------------------
# Forgot Password (ارسال OTP)
# ----------------------------
class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

    def validate_phone_number(self, value):
        if not User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("کاربری با این شماره یافت نشد.")
        return value


# ----------------------------
# Reset Password (تأیید OTP و تنظیم رمز)
# ----------------------------
class ResetPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8, validators=[validate_password])

    def validate(self, attrs):
        phone = attrs.get("phone_number")
        code = attrs.get("code")

        try:
            reset_code = PasswordResetCode.objects.filter(phone_number=phone, code=code).latest("created_at")
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError("کد وارد شده معتبر نیست.")

        if not reset_code.is_valid():
            raise serializers.ValidationError("کد منقضی شده است.")

        attrs["user"] = User.objects.get(phone_number=phone)
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        phone_number = self.validated_data["phone_number"]
        code = self.validated_data["code"]
        new_password = self.validated_data["new_password"]

        with transaction.atomic():
            otp_obj = PasswordResetCode.objects.select_for_update().filter(
                phone_number=phone_number,
                code=code,
                is_used=False
            ).latest("created_at")

            if not otp_obj.is_valid():
                raise serializers.ValidationError("کد منقضی شده یا استفاده شده است.")

            user.password = make_password(new_password)
            user.save(update_fields=["password"])

            otp_obj.is_used = True
            otp_obj.save(update_fields=["is_used"])

        return user


# ----------------------------
# OTP Verification Serializers
# ----------------------------
class PhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, required=False)


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        phone = attrs.get('phone_number')
        code = attrs.get('code')
        try:
            otp = PasswordResetCode.objects.filter(phone_number=phone, code=code, is_used=False).latest('created_at')
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError("کد اشتباه یا منقضی است.")

        if not otp.is_valid():
            raise serializers.ValidationError("کد منقضی شده یا استفاده‌شده است.")

        user = User.objects.get(phone_number=phone)
        user.is_active = True
        user.save(update_fields=['is_active'])
        otp.is_used = True
        otp.save(update_fields=['is_used'])

        attrs['user'] = user
        return attrs