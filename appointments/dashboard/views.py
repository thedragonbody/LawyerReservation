from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ClientAppointmentSerializer,
    DashboardMetricsSerializer,
    LawyerAppointmentSerializer,
)
from .services import (
    DashboardAnalyticsService,
    DashboardFilterParams,
    get_filtered_appointments,
)


class ClientDashboardView(generics.ListAPIView):
    serializer_class = ClientAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_filtered_appointments(self.request.user, self.request)


class LawyerDashboardView(generics.ListAPIView):
    serializer_class = LawyerAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_filtered_appointments(self.request.user, self.request)


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filters = DashboardFilterParams.from_request(request)
        service = DashboardAnalyticsService(request.user, filters)
        metrics = service.get_metrics()
        serializer = DashboardMetricsSerializer(metrics)
        return Response(serializer.data)


class DashboardExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filters = DashboardFilterParams.from_request(request)
        service = DashboardAnalyticsService(request.user, filters)

        export_format = request.GET.get("format", "csv").lower()

        if export_format not in {"csv"}:
            return Response(
                {"detail": "Only CSV export is currently supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rows = list(service.iter_export_rows())
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="dashboard_export.csv"'

        import csv

        writer = csv.writer(response)
        for row in rows:
            writer.writerow(row)

        return response
