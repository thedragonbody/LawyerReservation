from django.urls import path
from .views import (
    CaseListCreateView,
    CaseDetailView,
    CaseCommentCreateView,
    CaseCommentListView,
    CaseCommentDetailView
)

urlpatterns = [
    # پرونده‌ها
    path('cases/', CaseListCreateView.as_view(), name='case-list-create'),
    path('cases/<int:pk>/', CaseDetailView.as_view(), name='case-detail'),

    # کامنت‌های پرونده
    path('cases/<int:case_id>/comments/', CaseCommentListView.as_view(), name='case-comment-list'),
    path('cases/<int:case_id>/comments/create/', CaseCommentCreateView.as_view(), name='case-comment-create'),
    path('comments/<int:pk>/', CaseCommentDetailView.as_view(), name='case-comment-detail'),
]