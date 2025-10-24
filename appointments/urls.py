from django.urls import path

from .integrations.views import (
    CalendarOAuthCallbackView,
    CalendarOAuthConnectView,
    CalendarOAuthRefreshView,
    CalendarOAuthStartView,
    CalendarOAuthStatusView,
)
from .views import (
    CancelOnlineAppointmentAPIView,
    OnlineAppointmentCreateView,
    OnlineAppointmentListView,
    OnlineSlotListView,
    OnsiteAppointmentDetailView,
    OnsiteAppointmentListCreateView,
    OnsiteSlotDetailView,
    OnsiteSlotListCreateView,
    RescheduleOnlineAppointmentAPIView,
)

app_name = "appointments"


urlpatterns = [
    path('slots/<int:lawyer_id>/', OnlineSlotListView.as_view(), name='online-slot-list'),
    path('appointments/create/', OnlineAppointmentCreateView.as_view(), name='online-appointment-create'),
    path('appointments/', OnlineAppointmentListView.as_view(), name='online-appointment-list'),
    path('appointments/<int:pk>/cancel/', CancelOnlineAppointmentAPIView.as_view(), name='online-appointment-cancel'),
    path('appointments/<int:pk>/reschedule/', RescheduleOnlineAppointmentAPIView.as_view(), name='online-appointment-reschedule'),
    path('onsite/slots/', OnsiteSlotListCreateView.as_view(), name='onsite-slot-list-create'),
    path('onsite/slots/<int:pk>/', OnsiteSlotDetailView.as_view(), name='onsite-slot-detail'),
    path('onsite/appointments/', OnsiteAppointmentListCreateView.as_view(), name='onsite-appointment-list-create'),
    path('onsite/appointments/<int:pk>/', OnsiteAppointmentDetailView.as_view(), name='onsite-appointment-detail'),
    path('calendar/oauth/<str:provider>/start/', CalendarOAuthStartView.as_view(), name='calendar-oauth-start'),
    path('calendar/oauth/<str:provider>/callback/', CalendarOAuthCallbackView.as_view(), name='calendar-oauth-callback'),
    path('calendar/oauth/<str:provider>/refresh/', CalendarOAuthRefreshView.as_view(), name='calendar-oauth-refresh'),
    path('calendar/oauth/<str:provider>/status/', CalendarOAuthStatusView.as_view(), name='calendar-oauth-status'),
    path('calendar/oauth/<str:provider>/connect/', CalendarOAuthConnectView.as_view(), name='calendar-oauth-connect'),
]
