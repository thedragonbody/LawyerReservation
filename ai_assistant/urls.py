from django.urls import path
from .views import AskAIView, AIQuestionListView, CreateSubscriptionPaymentView

urlpatterns = [
    path("ask/", AskAIView.as_view(), name="ask-ai"),
    path("history/", AIQuestionListView.as_view(), name="ai-history"),
    path("subscribe/create-payment/", CreateSubscriptionPaymentView.as_view(), name="create-subscription-payment"),
]
