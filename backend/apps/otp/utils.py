from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import random
import string
from .models import OTPRecord


def generate_code(length=6):
    return ''.join(random.choices(string.digits, k=length))


def create_otp(phone: str) -> str:
    # Invalidate any previous unused OTPs for this phone
    OTPRecord.objects.filter(phone=phone, is_used=False).update(is_used=True)
    
    expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
    code = generate_code(getattr(settings, 'OTP_LENGTH', 6))
    
    OTPRecord.objects.create(
        phone=phone,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
    )
    return code


def verify_otp(phone: str, code: str) -> tuple[bool, str]:
    try:
        record = OTPRecord.objects.filter(
            phone=phone, is_used=False
        ).latest('created_at')
    except OTPRecord.DoesNotExist:
        return False, 'No OTP found for this phone number.'

    if record.is_expired:
        return False, 'OTP has expired. Please request a new one.'

    if record.attempts >= 5:
        return False, 'Too many failed attempts. Please request a new OTP.'

    if record.code != code:
        record.attempts += 1
        record.save(update_fields=['attempts'])
        remaining = 5 - record.attempts
        return False, f'Invalid OTP. {remaining} attempt(s) remaining.'

    record.is_used = True
    record.save(update_fields=['is_used'])
    return True, 'OTP verified successfully.'
