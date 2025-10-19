import requests
from django.conf import settings

def send_sms(phone_number: str, message: str):
    """
    شبیه‌سازی ارسال پیامک.
    بعداً می‌تونی با API واقعی مثل Kavenegar یا Twilio جایگزین کنی.
    """
    print(f"📩 SMS to {phone_number}: {message}")
    # اگر خواستی بعداً اضافه کنی:
    # requests.post("https://api.kavenegar.com/v1/{API_KEY}/sms/send.json", data={...})