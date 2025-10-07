from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LawyerReviewViewSet

router = DefaultRouter()
router.register(r"reviews", LawyerReviewViewSet, basename="reviews")

urlpatterns = [
    path("", include(router.urls)),
]