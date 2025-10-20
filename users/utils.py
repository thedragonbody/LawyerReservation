def register_device_for_user(user, request):
    """ثبت یا بروزرسانی دستگاه هنگام ورود"""
    from client_profile.models import ClientProfile, Device
    cp, _ = ClientProfile.objects.get_or_create(user=user)
    ip = request.META.get('REMOTE_ADDR')
    ua = request.META.get('HTTP_USER_AGENT', '')[:500]
    name = ua.split(')')[-1].strip() if ua else ''
    Device.objects.update_or_create(
        client=cp,
        ip_address=ip,
        user_agent=ua,
        defaults={'name': name, 'revoked': False}
    )
    cp.last_login_ip = ip
    cp.last_login_user_agent = ua
    cp.save(update_fields=['last_login_ip', 'last_login_user_agent'])