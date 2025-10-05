from django.urls import path
from .views import (
    NotificationListView,
    NotificationCreateView,
    NotificationRetrieveView,
    NotificationMarkReadView,
    NotificationDeleteView
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notifications-list'),
    path('create/', NotificationCreateView.as_view(), name='notifications-create'),
    path('<int:id>/', NotificationRetrieveView.as_view(), name='notifications-retrieve'),
    path('<int:id>/mark-read/', NotificationMarkReadView.as_view(), name='notifications-mark-read'),
    path('<int:id>/delete/', NotificationDeleteView.as_view(), name='notifications-delete'),
]