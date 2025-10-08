from django.urls import path
from .views import SendMessageView, GetMessagesView, TypingIndicatorView

urlpatterns = [
    path('send-message/', SendMessageView.as_view(), name='send-message'),
    path('get-messages/<int:lawyer_id>/<int:client_id>/', GetMessagesView.as_view(), name='get-messages'),
    path('typing-indicator/', TypingIndicatorView.as_view(), name='typing-indicator'),

]