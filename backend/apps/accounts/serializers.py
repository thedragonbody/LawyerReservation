from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('phone', 'first_name', 'last_name', 'role')

    def validate_role(self, value):
        if value not in ('lawyer', 'customer'):
            raise serializers.ValidationError('Role must be lawyer or customer.')
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'phone', 'first_name', 'last_name', 'full_name',
                  'role', 'is_staff', 'is_superuser', 'is_phone_verified', 'avatar', 'avatar_url', 'created_at')
        read_only_fields = ('id', 'phone', 'role', 'is_staff', 'is_superuser', 'is_phone_verified', 'avatar_url', 'created_at')

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

    @staticmethod
    def get_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
