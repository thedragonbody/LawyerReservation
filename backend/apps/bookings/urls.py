from django.urls import path
from . import views

urlpatterns = [
    path('', views.customer_bookings, name='bookings'),
    path('lawyer/', views.lawyer_bookings, name='lawyer_bookings'),
    path('<uuid:booking_id>/', views.booking_detail, name='booking_detail'),
    path('<uuid:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('<uuid:booking_id>/documents/', views.booking_documents, name='booking_documents'),
    path('<uuid:booking_id>/documents/<uuid:doc_id>/', views.delete_document, name='delete_document'),
    path('slots/<uuid:lawyer_id>/', views.available_slots, name='available_slots'),
]
