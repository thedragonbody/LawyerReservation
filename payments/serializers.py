from rest_framework import serializers
from .models import Payment
from appointments.models import Appointment

class PaymentSerializer(serializers.ModelSerializer):
    appointment = serializers.PrimaryKeyRelatedField(
        queryset=Appointment.objects.all()
    )
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "appointment",
            "user",
            "amount",
            "payment_method",
            "status",
            "transaction_id",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["status", "transaction_id", "created_at", "updated_at"]