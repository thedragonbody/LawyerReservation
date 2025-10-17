from rest_framework import serializers
from .models import Slot, Appointment
from urllib.parse import quote



class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slot
        fields = ['id', 'lawyer', 'start_time', 'end_time', 'is_booked', 'price']
        read_only_fields = ['lawyer', 'is_booked', 'price']

class AppointmentSerializer(serializers.ModelSerializer):
    lawyer = serializers.ReadOnlyField(source='slot.lawyer.id')
    client = serializers.ReadOnlyField(source='client.id')

    class Meta:
        model = Appointment
        fields = [
            'id', 'lawyer', 'client', 'slot', 'status', 'description',
            'location_name', 'latitude', 'longitude', 'rescheduled_from',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['lawyer', 'client', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        slot = attrs.get('slot')
        if slot.is_booked:
            raise serializers.ValidationError("This slot is already booked.")
        if slot.end_time <= slot.start_time:
            raise serializers.ValidationError("Slot end_time must be after start_time.")
        return attrs

    def create(self, validated_data):
        slot = validated_data['slot']
        slot.is_booked = True
        slot.save()
        appointment = super().create(validated_data)
        return appointment
    
    map_link = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ['id', 'lawyer', 'client', 'slot', 'status', 'description', 'location', 'map_link']

    def get_map_link(self, obj):
        if obj.location:
            return f"https://www.google.com/maps/search/?api=1&query={quote(obj.location)}"
        return None