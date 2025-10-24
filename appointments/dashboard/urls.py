from django.urls import path

from .views import (
    ClientDashboardView,
    DashboardExportView,
    DashboardStatsView,
    LawyerDashboardView,
)


urlpatterns = [
    path("client/", ClientDashboardView.as_view(), name="client-dashboard"),
    path("lawyer/", LawyerDashboardView.as_view(), name="lawyer-dashboard"),
    path("stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("export/", DashboardExportView.as_view(), name="dashboard-export"),
]
