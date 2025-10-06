"""
URL configuration for AloVakil project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from rest_framework.permissions import IsAuthenticated
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

# اضافه کردن drf-spectacular
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # اپ‌ها
    path('users/', include('users.urls')),
    path('appointments/', include('appointments.urls')),
    path('notifications/', include('notifications.urls')),
    path("payments/", include("payments.urls")),
    path("cases", include("cases.urls")),
    path('api/searchs/', include('searchs.urls')),
    path('api/chat/', include('chat.urls')),

    # مستندات API
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[IsAuthenticated]), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[IsAuthenticated]), name="swagger-ui"),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)