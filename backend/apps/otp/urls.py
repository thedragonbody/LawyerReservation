from django.urls import path
from . import views

urlpatterns = [
    path('resend/', views.resend_otp, name='resend_otp'),
]
