from django.urls import path
from .views import OnlineSlotListView, OnlineAppointmentCreateView, OnlineAppointmentListView, CancelOnlineAppointmentAPIView, RescheduleOnlineAppointmentAPIView

urlpatterns = [
    path('slots/<int:lawyer_id>/', OnlineSlotListView.as_view(), name='online-slot-list'),
    path('appointments/create/', OnlineAppointmentCreateView.as_view(), name='online-appointment-create'),
    path('appointments/', OnlineAppointmentListView.as_view(), name='online-appointment-list'),
    path('appointments/<int:pk>/cancel/', CancelOnlineAppointmentAPIView.as_view(), name='online-appointment-cancel'),
    path('appointments/<int:pk>/reschedule/', RescheduleOnlineAppointmentAPIView.as_view(), name='online-appointment-reschedule'),
]