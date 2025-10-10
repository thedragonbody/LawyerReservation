from rest_framework import serializers
from .models import AIQuestion

class AIQuestionSerializer(serializers.ModelSerializer):
    PERSONAS = [
        ("assistant", "Assistant (ساده)"),
        ("lawyer", "Lawyer (رسمی و حقوقی)"),
        ("judge", "Judge (قاضی، رسمی و تحلیل دقیق)"),
    ]

    persona = serializers.ChoiceField(choices=PERSONAS, default="assistant")

    class Meta:
        model = AIQuestion
        fields = ["id", "question", "answer", "persona", "created_at", "answered_at"]
        read_only_fields = ["id", "answer", "created_at", "answered_at"]

class SubscriptionCreateSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(choices=[("idpay","idpay"),("zarinpal","zarinpal")], default="idpay")