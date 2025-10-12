from django.urls import path
from .views import ClientDashboardView, LawyerDashboardView, DashboardStatsView

urlpatterns = [
    path('client/', ClientDashboardView.as_view(), name='client-dashboard'),
    path('lawyer/', LawyerDashboardView.as_view(), name='lawyer-dashboard'),
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),

]