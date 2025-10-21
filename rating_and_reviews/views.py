from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import status
from django.db.models import Q # برای جستجوی دقیق‌تر

from .models import LawyerReview
from .serializers import LawyerReviewSerializer
from .tasks import notify_lawyer_of_new_review_task # 🚀 Celery Task

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    فقط صاحب ریویو (کلاینت) یا ادمین (Staff) می‌تواند ویرایش یا حذف کند.
    """
    def has_object_permission(self, request, view, obj):
        # ادمین مجاز است
        if request.user.is_staff:
            return True
        
        # صاحب ریویو مجاز است (کسی که در relation نقش client را دارد)
        return obj.relation.client.user == request.user

class LawyerReviewViewSet(viewsets.ModelViewSet):
    """
    ویوست کامل برای ریویو و امتیاز وکلا.
    - list, retrieve: AllowAny (فقط تایید شده)
    - create: IsAuthenticated (فقط کلاینت صاحب Relation)
    - update, destroy: IsOwnerOrAdmin
    """
    serializer_class = LawyerReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # فیلتر بر اساس lawyer_profile_id در relation
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
        # Eager loading برای جلوگیری از N+1 queries
        qs = LawyerReview.objects.select_related(
            "relation__lawyer__user", 
            "relation__client__user"
        ).order_by("-created_at")
        
        user = self.request.user
        
        if user.is_authenticated and user.is_staff:
            # ادمین همه review‌ها را می‌بیند
            return qs
            
        # کاربران عادی (مجاز یا غیرمجاز) فقط review‌های تایید شده را می‌بینند
        # اگر وکیل هست، reviewهای خودش هم جزو لیستش است
        return qs.filter(is_approved=True)

    def perform_create(self, serializer):
        user = self.request.user
        relation = serializer.validated_data.get("relation")

        # 💡 NOTE: ولیدیشن‌های اصلی (مثل مجاز بودن کاربر و عدم تکرار) در سریالایزر انجام شده‌اند.
        
        # 1. ایجاد review با is_approved=False به طور پیشفرض
        review = serializer.save(is_approved=False)

        # 2. 🚀 اطلاع‌رسانی به وکیل (Asynchronous via Celery)
        lawyer_user = review.relation.lawyer.user
        client_full_name = review.relation.client.user.get_full_name()
        rating = review.rating
        
        notify_lawyer_of_new_review_task.delay(
            lawyer_user.id,
            client_full_name,
            rating
        )

    def perform_update(self, serializer):
        review = serializer.instance
        user = self.request.user

        # 1. چک دسترسی ویرایش (قبلاً در IsOwnerOrAdmin و get_permissions چک شده، اما برای اطمینان مجدداً بررسی می‌شود.)
        if not (user.is_staff or review.relation.client.user == user):
            # اگرچه این خط نباید اجرا شود، اما برای امنیت می‌ماند.
            raise PermissionDenied("شما اجازه ویرایش این ریویو را ندارید.")

        # 2. امن کردن فیلد reply: فقط وکیل یا ادمین می‌تواند پاسخ دهد
        if "reply" in serializer.validated_data:
            # در اینجا باید user را با lawyer_user مقایسه کنیم
            lawyer_user = review.relation.lawyer.user
            if not (user == lawyer_user or user.is_staff):
                raise PermissionDenied("شما اجازه پاسخ به این ریویو را ندارید.")

        serializer.save()