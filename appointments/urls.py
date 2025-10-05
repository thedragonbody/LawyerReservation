from django.urls import path
from .views import AppointmentCreateView, AppointmentPaymentCallbackView

urlpatterns = [
    # ایجاد درخواست پرداخت و رزرو بعد از پرداخت
    path('create/', AppointmentCreateView.as_view(), name='appointment-create'),

    # Callback بعد از پرداخت موفق
    path('payment-callback/', AppointmentPaymentCallbackView.as_view(), name='appointment-payment-callback'),
]