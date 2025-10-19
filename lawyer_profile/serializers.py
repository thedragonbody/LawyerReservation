from rest_framework import serializers
from .models import LawyerProfile

class LawyerProfileSerializer(serializers.ModelSerializer):
    office = serializers.SerializerMethodField()
    is_online = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField(source='user.get_full_name')
    phone_number = serializers.ReadOnlyField(source='user.phone_number')

    class Meta:
        model = LawyerProfile
        fields = [
            "id",
            "full_name",
            "phone_number",
            "expertise",
            "specialization",
            "degree",
            "experience_years",
            "status",
            "is_online",
            "license_number",
            "city",
            "region",
            "bio",
            "avatar",
            "office",
            "created_at",
        ]

    def get_office(self, obj):
        return obj.get_office_location()