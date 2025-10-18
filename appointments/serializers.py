from rest_framework import serializers
from .models import Slot, Appointment


# ----------------------------
# Slot Serializer
# ----------------------------
class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slot
        fields = ['id', 'lawyer', 'start_time', 'end_time', 'is_booked', 'price']
        read_only_fields = ['lawyer', 'is_booked', 'price']


# ----------------------------
# Appointment Serializer
# ----------------------------
class AppointmentSerializer(serializers.ModelSerializer):
    lawyer = serializers.ReadOnlyField(source='slot.lawyer.id')
    client = serializers.ReadOnlyField(source='client.id')
    lawyer_office = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'lawyer', 'client', 'slot', 'status', 'description',
            'location', 'rescheduled_from', 'created_at', 'updated_at', 'lawyer_office'
        ]
        read_only_fields = ['lawyer', 'client', 'status', 'created_at', 'updated_at', 'lawyer_office']

    def get_lawyer_office(self, obj):
        # اگر slot یا lawyer نباشد None برگردان
        lawyer = getattr(obj.slot, "lawyer", None)
        if lawyer:
            return lawyer.get_office_location()
        return None

    def validate(self, attrs):
        slot = attrs.get('slot')
        if not slot:
            raise serializers.ValidationError("Slot must be provided.")
        if slot.is_booked:
            raise serializers.ValidationError("This slot is already booked.")
        if slot.end_time <= slot.start_time:
            raise serializers.ValidationError("Slot end_time must be after start_time.")
        return attrs

    def create(self, validated_data):
        slot = validated_data['slot']
        slot.is_booked = True
        slot.save(update_fields=['is_booked'])
        appointment = super().create(validated_data)
        return appointment


# ----------------------------
# Appointment Detail Serializer
# ----------------------------
class AppointmentDetailSerializer(serializers.ModelSerializer):
    lawyer_location = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id',
            'lawyer',
            'lawyer_location',
            'client',
            'slot',
            'status',
            'description',
            'location',  # لوکیشن اختصاصی جلسه اگر وجود داشت
        ]
        read_only_fields = ['lawyer', 'lawyer_location', 'client', 'status']

    def get_lawyer_location(self, obj):
        if obj.slot and hasattr(obj.slot, 'lawyer'):
            return obj.slot.lawyer.get_office_location()
        return None