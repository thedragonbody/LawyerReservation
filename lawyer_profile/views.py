from rest_framework import generics, permissions
from .models import LawyerProfile
from .serializers import LawyerProfileSerializer

class LawyerProfileListView(generics.ListAPIView):
    """
    لیست همه وکلای عمومی (نمایش وضعیت و تخصص)
    """
    queryset = LawyerProfile.objects.all()
    serializer_class = LawyerProfileSerializer
    permission_classes = [permissions.AllowAny]

class LawyerProfileDetailView(generics.RetrieveAPIView):
    """
    جزییات یک وکیل خاص
    """
    queryset = LawyerProfile.objects.all()
    serializer_class = LawyerProfileSerializer
    permission_classes = [permissions.AllowAny]