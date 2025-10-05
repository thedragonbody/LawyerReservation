from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Case, CaseComment
from .serializers import CaseSerializer, CaseCommentSerializer
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from notifications.models import Notification
from common.utils import send_sms

# ==============================
# Permissions helper
# ==============================
class IsOwnerOrLawyer(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if hasattr(user, "lawyer_profile") and obj.lawyer == user.lawyer_profile:
            return True
        return False

# ==============================
# Pagination
# ==============================
class CasePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

# ==============================
# Case Views
# ==============================
class CaseListCreateView(generics.ListCreateAPIView):
    queryset = Case.objects.filter(is_public=True)
    serializer_class = CaseSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = CasePagination  

    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, "lawyer_profile"):
            raise PermissionDenied("فقط وکلا می‌توانند پرونده ایجاد کنند.")
        case = serializer.save(lawyer=user.lawyer_profile)

        # Notification داخلی برای همه کاربران (مثلاً اگر نیاز باشد)
        Notification.objects.create(
            user=user,  # یا می‌توانید یک لیست از کاربران داشته باشید
            title="پرونده جدید ایجاد شد",
            message=f"پرونده '{case.title}' توسط {user.get_full_name()} ایجاد شد."
        )

        # پیامک برای وکیل (اختیاری)
        send_sms(user.phone_number, f"پرونده جدید '{case.title}' ایجاد شد.")

class CaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrLawyer]

# ==============================
# CaseComment Views
# ==============================
class CaseCommentCreateView(generics.CreateAPIView):
    serializer_class = CaseCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        case_id = self.kwargs["case_id"]
        case = get_object_or_404(Case, id=case_id)
        comment = serializer.save(user=self.request.user, case=case, parent=None)

        # Notification برای وکیل پرونده
        Notification.objects.create(
            user=case.lawyer.user,
            title="کامنت جدید روی پرونده شما",
            message=f"{self.request.user.get_full_name()} روی پرونده '{case.title}' کامنت گذاشت."
        )

        # پیامک برای وکیل
        send_sms(case.lawyer.user.phone_number,
                 f"کامنت جدید روی پرونده '{case.title}' توسط {self.request.user.get_full_name()}.")

class CaseCommentListView(generics.ListAPIView):
    serializer_class = CaseCommentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        case_id = self.kwargs["case_id"]
        return CaseComment.objects.filter(case_id=case_id, parent=None)

class CaseCommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CaseComment.objects.all()
    serializer_class = CaseCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        if self.get_object().user != self.request.user:
            raise PermissionDenied("فقط صاحب کامنت می‌تواند ویرایش کند.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        is_comment_owner = instance.user == user
        is_case_lawyer = hasattr(user, "lawyer_profile") and instance.case.lawyer == user.lawyer_profile
        if not (is_comment_owner or is_case_lawyer):
            raise PermissionDenied("شما اجازه حذف این کامنت را ندارید.")
        instance.delete()

class CaseCommentReplyView(generics.CreateAPIView):
    """
    ایجاد ریپلای روی یک کامنت.
    """
    serializer_class = CaseCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        parent_id = self.kwargs["comment_id"]
        parent_comment = get_object_or_404(CaseComment, id=parent_id)

        # فقط کاربر احراز هویت شده می‌تواند ریپلای بگذارد
        user = self.request.user
        reply = serializer.save(
            user=user,
            case=parent_comment.case,
            parent=parent_comment
        )

        # Notification برای صاحب کامنت اصلی
        Notification.objects.create(
            user=parent_comment.user,
            title="ریپلای جدید روی کامنت شما",
            message=f"{user.get_full_name()} به کامنت شما روی پرونده '{parent_comment.case.title}' پاسخ داد."
        )

        # پیامک برای صاحب کامنت اصلی
        send_sms(parent_comment.user.phone_number,
                 f"ریپلای جدید روی کامنت شما توسط {user.get_full_name()} روی پرونده '{parent_comment.case.title}'.")