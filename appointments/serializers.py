from django.utils import timezone
from rest_framework import serializers

from .models import (
    OnlineAppointment,
    OnlineSlot,
    OnsiteAppointment,
    OnsiteSlot,
)

class OnlineSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlineSlot
        fields = ['id', 'lawyer', 'start_time', 'end_time', 'is_booked', 'price']

class OnlineAppointmentSerializer(serializers.ModelSerializer):
    slot_start = serializers.SerializerMethodField()
    slot_end = serializers.SerializerMethodField()
    lawyer_summary = serializers.SerializerMethodField()

    class Meta:
        model = OnlineAppointment
        fields = [
            'id',
            'lawyer',
            'client',
            'slot',
            'status',
            'google_meet_link',
            'description',
            'slot_start',
            'slot_end',
            'lawyer_summary',
        ]
        read_only_fields = [
            'status',
            'google_meet_link',
            'client',
            'slot_start',
            'slot_end',
            'lawyer_summary',
        ]

    def _get_slot(self, obj):
        return getattr(obj, 'slot', None)

    def _get_lawyer(self, obj):
        return getattr(obj, 'lawyer', None)

    def get_slot_start(self, obj):
        slot = self._get_slot(obj)
        return slot.start_time if slot else None

    def get_slot_end(self, obj):
        slot = self._get_slot(obj)
        return slot.end_time if slot else None

    def get_lawyer_summary(self, obj):
        lawyer = self._get_lawyer(obj)
        if not lawyer:
            return None

        user = getattr(lawyer, 'user', None)
        full_name = user.get_full_name() if user else None
        phone_number = getattr(user, 'phone_number', None) if user else None

        summary = {
            'id': lawyer.id,
            'name': full_name,
            'phone_number': phone_number,
            'status': lawyer.status,
            'expertise': lawyer.expertise,
            'specialization': lawyer.specialization,
        }

        if lawyer.avatar:
            summary['avatar'] = lawyer.avatar.url

        return summary

class OnlineAppointmentCancelSerializer(serializers.Serializer):
    # برای cancel فقط نیاز به تایید اقدام داریم (اختیاری میتونی دلیل هم اضافه کنی)
    confirm = serializers.BooleanField(default=True)

class OnlineAppointmentRescheduleSerializer(serializers.Serializer):
    new_slot_id = serializers.IntegerField()


class OnsiteSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnsiteSlot
        fields = [
            "id",
            "lawyer",
            "start_time",
            "end_time",
            "office_address",
            "office_latitude",
            "office_longitude",
            "is_booked",
        ]
        read_only_fields = ["lawyer", "is_booked"]


class OnsiteAppointmentSerializer(serializers.ModelSerializer):
    slot = serializers.PrimaryKeyRelatedField(queryset=OnsiteSlot.objects.all())

    class Meta:
        model = OnsiteAppointment
        fields = [
            "id",
            "lawyer",
            "client",
            "slot",
            "status",
            "office_address",
            "office_latitude",
            "office_longitude",
            "notes",
        ]
        read_only_fields = [
            "lawyer",
            "client",
            "office_address",
            "office_latitude",
            "office_longitude",
        ]

    def validate_slot(self, slot):
        if slot.start_time <= timezone.now():
            raise serializers.ValidationError("امکان رزرو اسلات گذشته وجود ندارد.")
        if slot.is_booked:
            raise serializers.ValidationError("این اسلات قبلاً رزرو شده است.")
        return slot

    def create(self, validated_data):
        slot = validated_data["slot"]
        validated_data["lawyer"] = slot.lawyer
        validated_data["office_address"] = slot.office_address
        validated_data["office_latitude"] = slot.office_latitude
        validated_data["office_longitude"] = slot.office_longitude
        return super().create(validated_data)