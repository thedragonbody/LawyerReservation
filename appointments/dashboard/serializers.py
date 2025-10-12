from rest_framework import serializers
from appointments.models import Appointment, Slot

class ClientAppointmentSerializer(serializers.ModelSerializer):
    lawyer_name = serializers.CharField(source='lawyer.user.get_full_name', read_only=True)
    slot_time = serializers.DateTimeField(source='slot.start_time', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'lawyer_name', 'slot_time', 'status', 'session_type', 'location', 'online_link']

class LawyerAppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.user.get_full_name', read_only=True)
    slot_time = serializers.DateTimeField(source='slot.start_time', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'client_name', 'slot_time', 'status', 'session_type', 'location', 'online_link']