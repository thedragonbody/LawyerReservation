def really_send_sms(phone_number: str, message: str):
    """
    ارسال پیامک به شماره داده‌شده.
    در اینجا می‌توان gateway واقعی (مثل Kavenegar, Twilio) را جایگذاری کرد.
    """
    print(f"Sending SMS to {phone_number}: {message}")
    # TODO: اتصال به سرویس واقعی پیامک