from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import AIQuestion
from .serializers import AIQuestionSerializer
from .utils import ask_ai

class AskAIView(generics.CreateAPIView):
    queryset = AIQuestion.objects.all()
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        question = self.request.data.get("question", "")
        user_role = None
        if hasattr(self.request.user, "lawyer_profile"):
            user_role = "lawyer"
        elif hasattr(self.request.user, "client_profile"):
            user_role = "client"

        # فراخوانی AI
        answer = ask_ai(question, user_role=user_role)

        serializer.save(
            user=self.request.user,
            answer=answer,
            answered_at=timezone.now()
        )


class AIQuestionListView(generics.ListAPIView):
    queryset = AIQuestion.objects.all()
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AIQuestion.objects.filter(user=self.request.user).order_by("-created_at")