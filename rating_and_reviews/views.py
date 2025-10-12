from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import LawyerReview
from .serializers import LawyerReviewSerializer
from notifications.utils import send_notification

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
    - ایجاد: فقط کاربران authenticated، جلوگیری از duplicate review
    - ویرایش/حذف: فقط صاحب ریویو یا ادمین
    - ارسال نوتیف به وکیل هنگام ایجاد ریویو
    - فیلتر بر اساس وکیل و امتیاز
    - جستجو در کامنت و پاسخ
    - مرتب‌سازی بر اساس تاریخ و امتیاز
    """
    serializer_class = LawyerReviewSerializer
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

    def get_queryset(self):
        """
        لیست review‌ها:
        - فقط تایید شده‌ها برای کاربران عادی
        - همه review‌ها برای staff
        """
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return LawyerReview.objects.all().order_by("-created_at")
        return LawyerReview.objects.filter(is_approved=True).order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        relation = serializer.validated_data.get("relation")

        # جلوگیری از duplicate review برای یک relation
        if LawyerReview.objects.filter(relation=relation, relation__client__user=user).exists():
            raise ValidationError("شما قبلاً برای این رابطه ریویو ثبت کرده‌اید.")

        # ایجاد review با is_approved=False به طور پیشفرض
        review = serializer.save(is_approved=False)

        # اطلاع‌رسانی به وکیل
        send_notification(
            review.relation.lawyer.user,
            title="📝 نظر جدید درباره شما",
            message=f"{review.relation.client.user.get_full_name()} یک نظر جدید با امتیاز {review.rating} داده است."
        )

    def perform_update(self, serializer):
        review = serializer.instance
        user = self.request.user

        # بررسی اجازه ویرایش
        if not (user.is_staff or review.relation.client.user == user):
            raise PermissionDenied("شما اجازه ویرایش این ریویو را ندارید.")

        # امن کردن reply: فقط وکیل مربوطه یا admin می‌تواند reply بدهد
        if "reply" in serializer.validated_data:
            if not (user == review.relation.lawyer.user or user.is_staff):
                raise PermissionDenied("شما اجازه پاسخ به این ریویو را ندارید.")

        serializer.save()