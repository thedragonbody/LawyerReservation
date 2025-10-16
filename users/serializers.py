from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, ClientProfile, LawyerProfile
from .models import PasswordResetCode 

# ----------------------------
# User Serializer (با OTP)
# ----------------------------
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password'],
            is_active=False  # تا تایید OTP فعال نشود
        )
        # TODO: ارسال OTP به شماره کاربر
        return user


# ----------------------------
# Client Profile Serializer
# ----------------------------
class ClientProfileSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ClientProfile
        fields = ['national_id', 'created_at', 'updated_at', 'avatar']


# ----------------------------
# Lawyer Profile Serializer
# ----------------------------
class LawyerProfileSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = LawyerProfile
        fields = [
            'expertise', 'degree', 'experience_years', 'status',
            'document', 'bio', 'city', 'specialization',
            'created_at', 'updated_at', 'avatar'
        ]


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
# Lawyer List Serializer
# ----------------------------
class LawyerListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = LawyerProfile
        fields = ['id', 'full_name', 'expertise', 'degree', 'experience_years', 'status']

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


# ----------------------------
# Custom JWT Serializer
# ----------------------------
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # اطلاعات اضافی
        token['is_client'] = hasattr(user, 'client_profile')
        token['is_lawyer'] = hasattr(user, 'lawyer_profile')
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
        user.set_password(self.validated_data["new_password"])
        user.save()
        reset_code = PasswordResetCode.objects.filter(phone_number=self.validated_data["phone_number"], code=self.validated_data["code"]).latest("created_at")
        reset_code.is_used = True
        reset_code.save()
        return user