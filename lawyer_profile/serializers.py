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
        location = obj.get_office_location()
        if not location:
            return None

        meaningful_values = [
            location.get("address"),
            location.get("latitude"),
            location.get("longitude"),
            location.get("map_url"),
            location.get("map_embed_url"),
        ]
        if not any(value not in (None, "") for value in meaningful_values):
            return None

        latitude = location.get("latitude")
        longitude = location.get("longitude")

        return {
            "address": location.get("address"),
            "latitude": latitude,
            "longitude": longitude,
            "coordinates": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "map_url": location.get("map_url"),
            "map_embed_url": location.get("map_embed_url"),
        }
