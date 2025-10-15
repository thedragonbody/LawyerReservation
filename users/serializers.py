from rest_framework import serializers
from .models import User, ClientProfile, LawyerProfile
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
# ----------------------------
# User Serializer
# ----------------------------
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
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
        fields = ['expertise', 'degree', 'experience_years', 'status', 'document', 'created_at', 'updated_at', 'avatar']


# ----------------------------
# Change Password Serializer
# ----------------------------
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])


# ----------------------------
# Logout Serializer (برای blacklist JWT)
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

class LawyerListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = LawyerProfile
        fields = ['id', 'full_name', 'expertise', 'degree', 'experience_years', 'status']

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # اطلاعات اضافی
        token['email'] = user.email
        token['is_client'] = hasattr(user, 'clientprofile')
        token['is_lawyer'] = hasattr(user, 'lawyerprofile')
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            "id": self.user.id,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }
        return data
    
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uidb64']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid UID.")

        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError("Invalid or expired token.")

        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user