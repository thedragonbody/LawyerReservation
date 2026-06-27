from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .utils import create_otp


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp(request):
    phone = request.data.get('phone', '').strip()
    if not phone:
        return Response({'detail': 'Phone is required.'}, status=400)
    code = create_otp(phone)
    # send_sms(phone, f"Your Lexara OTP: {code}")
    return Response({'detail': 'OTP resent.', '_dev_otp': code})
