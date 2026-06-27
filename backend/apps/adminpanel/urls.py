from django.urls import path
from . import views

urlpatterns = [
    path('finance-overview/', views.finance_overview, name='admin_finance_overview'),
    path('commission/', views.commission_settings, name='admin_commission_settings'),
    path('discounts/', views.discounts, name='admin_discounts'),
    path('discounts/<uuid:discount_id>/', views.discount_detail, name='admin_discount_detail'),
    path('settlements/', views.settlements, name='admin_settlements'),
    path('settlements/<uuid:settlement_id>/', views.settlement_detail, name='admin_settlement_detail'),
    path('cancellations/', views.cancellation_logs, name='admin_cancellation_logs'),
    path('site-content/', views.site_content, name='admin_site_content'),
    path('overview/', views.overview, name='admin_overview'),
    path('users/', views.users, name='admin_users'),
    path('users/<uuid:user_id>/', views.user_detail, name='admin_user_detail'),
    path('lawyers/', views.lawyers, name='admin_lawyers'),
    path('lawyers/<uuid:lawyer_id>/', views.lawyer_detail, name='admin_lawyer_detail'),
    path('lawyers/<uuid:lawyer_id>/verify/', views.verify_lawyer, name='admin_lawyer_verify'),
    path('bookings/', views.bookings, name='admin_bookings'),
    path('bookings/<uuid:booking_id>/', views.booking_update, name='admin_booking_update'),
    path('documents/', views.documents, name='admin_documents'),
]

urlpatterns += [
    path('reviews/', views.reviews, name='admin_reviews'),
    path('reviews/<uuid:review_id>/', views.review_detail, name='admin_review_detail'),
    path('revenue/', views.revenue, name='admin_revenue'),
]
