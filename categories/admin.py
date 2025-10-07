from django.contrib import admin
from .models import Category

class SubCategoryInline(admin.TabularInline):
    model = Category
    fk_name = 'parent'
    extra = 1
    verbose_name = "زیر دسته"
    verbose_name_plural = "زیر دسته‌ها"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'parent', 'subcategories_count', 'created_at', 'updated_at')
    list_filter = ('parent',)
    search_fields = ('name',)
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [SubCategoryInline]

    def subcategories_count(self, obj):
        return obj.subcategories.count()
    subcategories_count.short_description = "تعداد زیر دسته‌ها"