from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import LawyerReview
from .serializers import LawyerReviewSerializer
from notifications.utils import send_notification
from rest_framework.exceptions import PermissionDenied

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    فقط صاحب ریویو یا ادمین می‌تواند ویرایش یا حذف کند
    """
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.relation.client.user == request.user


class LawyerReviewViewSet(viewsets.ModelViewSet):
    """
    ویوست کامل برای ریویو و امتیاز وکلا:
    - لیست و جزئیات: همه کاربران (فقط ریویوهای تایید شده)
    - ایجاد: فقط کاربران authenticated
    - ویرایش/حذف: فقط صاحب ریویو یا ادمین
    - ارسال نوتیف به وکیل هنگام ایجاد ریویو
    - فیلتر بر اساس وکیل و امتیاز
    - جستجو در کامنت و پاسخ
    - مرتب‌سازی بر اساس تاریخ و امتیاز
    """
    queryset = LawyerReview.objects.filter(is_approved=True).order_by("-created_at")
    serializer_class = LawyerReviewSerializer

    # فیلترها و جستجو
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['relation__lawyer', 'rating']
    search_fields = ['comment', 'reply']
    ordering_fields = ['created_at', 'rating']

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        elif self.action == "create":
            permission_classes = [permissions.IsAuthenticated]
        else:  # list, retrieve
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        review = serializer.save()
        # اطلاع‌رسانی به وکیل
        send_notification(
            review.relation.lawyer.user,
            title="📝 نظر جدید درباره شما",
            message=f"{review.relation.client.user.get_full_name()} یک نظر جدید با امتیاز {review.rating} داده است."
        )

    def perform_update(self, serializer):
        review = serializer.instance
        if not (self.request.user.is_staff or review.relation.client.user == self.request.user):
            raise PermissionDenied("شما اجازه ویرایش این ریویو را ندارید.")
        serializer.save()