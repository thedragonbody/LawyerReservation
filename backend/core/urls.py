from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/otp/', include('apps.otp.urls')),
    path('api/lawyers/', include('apps.lawyers.urls')),
    path('api/customers/', include('apps.customers.urls')),
    path('api/bookings/', include('apps.bookings.urls')),
    path('api/admin-panel/', include('apps.adminpanel.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
