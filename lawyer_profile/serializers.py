from rest_framework import serializers
from .models import LawyerProfile

class LawyerProfileSerializer(serializers.ModelSerializer):
    office_location = serializers.SerializerMethodField()

    class Meta:
        model = LawyerProfile
        fields = [
            'user', 'expertise', 'degree', 'experience_years', 'status',
            'document', 'bio', 'city', 'specialization', 'avatar',
            'office_address', 'office_location', 'created_at', 'updated_at'
        ]
        read_only_fields = ['status', 'created_at', 'updated_at', 'office_location']

    def get_office_location(self, obj):
        return obj.get_office_location()