from django.urls import path
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
]
