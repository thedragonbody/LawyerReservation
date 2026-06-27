from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User
from .serializers import RegisterSerializer, UserSerializer, TokenResponseSerializer
from apps.otp.utils import create_otp, verify_otp


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Step 1: register → sends OTP to phone."""
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    phone = ser.validated_data['phone']

    # Check duplicate
    if User.objects.filter(phone=phone).exists():
        return Response({'detail': 'Phone already registered.'}, status=400)

    user = ser.save()
    otp_code = create_otp(phone)

    # Development helper: print OTP in backend terminal while SMS provider is not connected.
    print("=" * 60)
    print(f"LEXARA DEV OTP for {phone}: {otp_code}")
    print("=" * 60)

    # In production, send via SMS here:
    # send_sms(phone, f"Your Lexara OTP: {otp_code}")
    # For development, return otp in response:
    return Response({
        'detail': 'OTP sent to your phone.',
        'phone': phone,
        '_dev_otp': otp_code,   # REMOVE IN PRODUCTION
    }, status=201)

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """Admin-only login with phone + password.

    This is separate from OTP user login. Only is_staff/is_superuser accounts can enter the admin panel.
    """
    phone = str(request.data.get('phone', '')).strip()
    password = str(request.data.get('password', ''))

    if not phone or not password:
        return Response({'detail': 'شماره موبایل و رمز عبور ادمین الزامی است.'}, status=400)

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response({'detail': 'ادمین با این شماره پیدا نشد.'}, status=404)

    if not user.check_password(password):
        return Response({'detail': 'رمز عبور ادمین اشتباه است.'}, status=400)

    if not (user.is_staff or user.is_superuser):
        return Response({'detail': 'این حساب دسترسی ادمین ندارد.'}, status=403)

    if not user.is_active:
        return Response({'detail': 'این حساب غیرفعال است.'}, status=403)

    tokens = TokenResponseSerializer.get_tokens(user)
    return Response({
        **tokens,
        'user': UserSerializer(user, context={'request': request}).data,
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    """Send OTP to existing user (login flow)."""
    phone = request.data.get('phone', '').strip()
    if not phone:
        return Response({'detail': 'Phone is required.'}, status=400)

    try:
        User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response({'detail': 'No account found with this phone number.'}, status=404)

    otp_code = create_otp(phone)
    # send_sms(phone, f"Your Lexara OTP: {otp_code}")

    return Response({
        'detail': 'OTP sent.',
        'phone': phone,
        '_dev_otp': otp_code,   # REMOVE IN PRODUCTION
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_and_login(request):
    """Verify OTP → issue JWT tokens."""
    phone = request.data.get('phone', '').strip()
    code = request.data.get('otp', '').strip()

    if not phone or not code:
        return Response({'detail': 'phone and otp are required.'}, status=400)

    ok, message = verify_otp(phone, code)
    if not ok:
        return Response({'detail': message}, status=400)

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=404)

    user.is_phone_verified = True
    user.save(update_fields=['is_phone_verified'])

    tokens = TokenResponseSerializer.get_tokens(user)
    return Response({
        **tokens,
        'user': UserSerializer(user, context={'request': request}).data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    from rest_framework_simplejwt.views import TokenRefreshView
    return TokenRefreshView.as_view()(request._request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user, context={'request': request}).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_me(request):
    ser = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
    except (TokenError, KeyError):
        pass
    return Response({'detail': 'Logged out.'})
