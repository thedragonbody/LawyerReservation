from rest_framework import serializers
from .models import Slot, Appointment
from common.choices import AppointmentStatus

class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slot
        fields = ['id', 'lawyer', 'start_time', 'end_time', 'is_booked', "price"]
        read_only_fields = ['lawyer', 'is_booked', "price"]

class AppointmentSerializer(serializers.ModelSerializer):
    lawyer = serializers.ReadOnlyField(source='slot.lawyer.id')
    client = serializers.ReadOnlyField(source='client.id')

    class Meta:
        model = Appointment
        fields = [
            'id', 'lawyer', 'client', 'slot', 'session_type', 'status', 'description',
            'location', 'online_link', 'transaction_id', 'cancellation_reason', 'rescheduled_from',
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