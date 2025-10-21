from rest_framework.throttling import SimpleRateThrottle

class SMSRequestThrottle(SimpleRateThrottle):
    # از نرخ تعریف شده در settings.py استفاده می کند
    scope = 'sms_request' 
    
    # متد کلید: یا IP را برمی گرداند یا شماره تلفن
    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            # اگر کاربر لاگین است، بر اساس ID کاربر محدود شود (که در RegisterView اتفاق نمی‌افتد)
            return self.cache_format % {
                'scope': self.scope,
                'ident': request.user.pk
            }
        
        # 1. محدودیت بر اساس IP برای کاربران ناشناس
        ip_addr = request.META.get('REMOTE_ADDR')
        
        # 2. محدودیت بر اساس شماره تلفن ارسالی (برای اطمینان بیشتر)
        phone_number = request.data.get('phone_number')

        # ترکیب کلیدها: قوی‌ترین محدودیت را اعمال می‌کنیم
        if phone_number:
            return self.cache_format % {
                'scope': self.scope,
                'ident': f'{ip_addr}:{phone_number}'
            }
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ip_addr
        }