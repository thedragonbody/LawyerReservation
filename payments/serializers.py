from rest_framework import serializers
from payments.models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "amount",
            "status",
            "payment_method",
            "transaction_id",
            "online_appointment",
        ]
        read_only_fields = ["status", "transaction_id"]