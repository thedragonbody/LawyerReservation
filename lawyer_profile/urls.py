from django.urls import path
from .views import LawyerProfileListView, LawyerProfileDetailView

urlpatterns = [
    path('lawyers/', LawyerProfileListView.as_view(), name='lawyer-list'),
    path('lawyers/<int:pk>/', LawyerProfileDetailView.as_view(), name='lawyer-detail'),
]