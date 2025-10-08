"""
URL configuration for AloVakil project.
Clean & optimized version.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Admin Panel
    path("admin/", admin.site.urls),

    # Local Apps
    path("users/", include("users.urls")),
    path("appointments/", include("appointments.urls")),
    path("notifications/", include("notifications.urls")),
    path("payments/", include("payments.urls")),
    path("cases/", include("cases.urls")),
    path("searchs/", include("searchs.urls")),
    path("chat/", include("chat.urls")),
    path("categories/", include("categories.urls")),
    path("rating_and_reviews/", include("rating_and_reviews.urls")),
    path("ai/assistant/", include("ai_assistant.urls")),
    
    # API Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

# --- Static & Media (Dev mode only) ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)