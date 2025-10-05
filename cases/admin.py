from django.contrib import admin
from .models import Case, CaseComment

# این کلاس Inline برای نمایش Comment ها زیر کیس
class CaseCommentInline(admin.TabularInline):  # یا StackedInline برای نمایش عمودی
    model = CaseComment
    extra = 0  # تعداد فرم‌های خالی اضافی برای ایجاد سریع
    readonly_fields = ("user", "created_at")  # می‌خوای فقط نمایش بده
    can_delete = True

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("title", "lawyer", "result", "is_public", "created_at")
    list_filter = ("result", "is_public", "created_at")
    search_fields = ("title", "lawyer__user__email")
    inlines = [CaseCommentInline]  # اضافه کردن Commentها به کیس

