from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Notification.objects.all().order_by("-created_at")
        return Notification.objects.filter(user=user).order_by("-created_at")

class NotificationCreateView(generics.CreateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        notification = serializer.save(user=self.request.user)

        # WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_{self.request.user.id}',
            {
                "type": "send_notification",
                "message": NotificationSerializer(notification).data
            }
        )

        # SMS
        phone_number = getattr(self.request.user, "phone_number", None)
        if phone_number:
            from common.utils import send_sms
            send_sms(phone_number, f"{notification.title}\n{notification.message}")

class NotificationRetrieveView(generics.RetrieveAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Notification.objects.all()
        return Notification.objects.filter(user=user)

class NotificationMarkReadView(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.status = Notification.Status.READ
        notification.save(update_fields=["status", "updated_at"])
        return Response(NotificationSerializer(notification).data)

class NotificationDeleteView(generics.DestroyAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Notification.objects.all()
        return Notification.objects.filter(user=user)

def send_notification_email(user, title, message):
    try:
        from django.core.mail import send_mail
        send_mail(subject=title, message=message, from_email=None, recipient_list=[user.email], fail_silently=False)
    except Exception:
        pass