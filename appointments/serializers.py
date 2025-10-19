from rest_framework import serializers
from .models import OnlineSlot, OnlineAppointment

class OnlineSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlineSlot
        fields = ['id', 'lawyer', 'start_time', 'end_time', 'is_booked', 'price']

class OnlineAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlineAppointment
        fields = ['id', 'lawyer', 'client', 'slot', 'status', 'google_meet_link', 'description']
        read_only_fields = ['status', 'google_meet_link', 'client']

class OnlineAppointmentCancelSerializer(serializers.Serializer):
    # برای cancel فقط نیاز به تایید اقدام داریم (اختیاری میتونی دلیل هم اضافه کنی)
    confirm = serializers.BooleanField(default=True)

class OnlineAppointmentRescheduleSerializer(serializers.Serializer):
    new_slot_id = serializers.IntegerField()