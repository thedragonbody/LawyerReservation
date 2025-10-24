from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ClientProfile, Device
from .serializers import SendOTPSerializer, VerifyOTPSerializer, DeviceSerializer
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from users.utils import send_sms_task_or_sync
from django.db import transaction
from users.models import User
from rest_framework.throttling import AnonRateThrottle

# simple rate limit classes (could use redis-backed throttles)
class OTPThrottle(AnonRateThrottle):
    scope = "otp"  # define in settings REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']

class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number']

        # find user or create inactive user
        user, created = User.objects.get_or_create(phone_number=phone, defaults={'is_active': False})
        client_profile, _ = ClientProfile.objects.get_or_create(user=user)

        # rate-limiting logic: check last send time
        if client_profile.phone_verification_sent_at and timezone.now() - client_profile.phone_verification_sent_at < timedelta(seconds=60):
            return Response({"detail":"Too many requests. Try later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        code = client_profile.generate_phone_code()

        # send sms via celery or sync
        send_sms_task_or_sync(phone, f"Your verification code: {code}")

        return Response({"detail":"OTP sent."}, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        user = get_object_or_404(User, phone_number=phone)
        client_profile = get_object_or_404(ClientProfile, user=user)

        # validate code & expiry (e.g., 10 minutes)
        if not client_profile.phone_verification_code or client_profile.phone_verification_code != code:
            return Response({"detail":"Invalid code."}, status=status.HTTP_400_BAD_REQUEST)
        if timezone.now() - client_profile.phone_verification_sent_at > timedelta(minutes=10):
            return Response({"detail":"Code expired."}, status=status.HTTP_400_BAD_REQUEST)

        # mark verified and activate user
        with transaction.atomic():
            client_profile.mark_phone_verified()
            user.is_active = True
            user.save(update_fields=['is_active'])

        # return tokens? we rely on JWT login flow; you can issue token here if wanted
        return Response({"detail":"Phone verified."}, status=status.HTTP_200_OK)


class ToggleFavoriteLawyerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lawyer_id):
        client_profile = getattr(request.user, 'client_profile', None)
        if not client_profile:
            return Response({"detail": "Only clients."}, status=status.HTTP_403_FORBIDDEN)

        LawyerProfile = __import__('lawyer_profile').lawyer_profile.models.LawyerProfile
        lawyer = get_object_or_404(LawyerProfile, pk=lawyer_id)

        if client_profile.favorites.filter(pk=lawyer.pk).exists():
            client_profile.favorites.remove(lawyer)
            favorited = False
        else:
            client_profile.favorites.add(lawyer)
            favorited = True

        return Response({"favorited": favorited})


class DeviceListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DeviceSerializer

    def get_queryset(self):
        client_profile = getattr(self.request.user, 'client_profile', None)
        if not client_profile:
            return Device.objects.none()
        return client_profile.devices.order_by('-last_seen', '-created_at')


class RevokeDeviceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        client_profile = getattr(request.user, 'client_profile', None)
        if not client_profile:
            return Response({"detail": "Only clients."}, status=status.HTTP_403_FORBIDDEN)

        device = get_object_or_404(Device, pk=pk, client=client_profile)
        device.mark_revoked()
        return Response({"detail": "Device revoked."}, status=status.HTTP_200_OK)


