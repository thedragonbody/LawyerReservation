from rest_framework import serializers
from .models import AIQuestion

class AIQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIQuestion
        fields = ["id", "question", "answer", "created_at", "answered_at"]