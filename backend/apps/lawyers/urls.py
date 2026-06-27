from django.urls import path
from . import views

urlpatterns = [
    path('justive/analyze/', views.justive_analyze, name='justive_analyze'),
    path('', views.LawyerListView.as_view(), name='lawyer_list'),
    path('<uuid:id>/', views.LawyerDetailView.as_view(), name='lawyer_detail'),
    path('me/profile/', views.my_profile, name='my_lawyer_profile'),
    path('me/dashboard/', views.lawyer_dashboard_stats, name='lawyer_dashboard'),
    path('me/availability/day/', views.availability_day, name='lawyer_availability_day'),
    path('<uuid:lawyer_id>/reviews/', views.add_review, name='add_review'),
]
