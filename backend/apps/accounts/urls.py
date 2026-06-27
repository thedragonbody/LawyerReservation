from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('request-otp/', views.request_otp, name='request_otp'),
    path('verify-otp/', views.verify_otp_and_login, name='verify_otp'),
    path('logout/', views.logout, name='logout'),
    path('me/', views.me, name='me'),
    path('me/update/', views.update_me, name='update_me'),
]
