from rest_framework import serializers
from .models import LawyerReview

class LawyerReviewSerializer(serializers.ModelSerializer):
    # نام وکیل و کلاینت از relation استخراج می‌شود
    lawyer_name = serializers.CharField(source="relation.lawyer.user.get_full_name", read_only=True)
    client_name = serializers.CharField(source="relation.client.user.get_full_name", read_only=True)
    
    # فیلد اضافی برای نمایش خلاصه ریویو
    short_comment = serializers.SerializerMethodField(read_only=True)
    
    # بررسی اینکه آیا کاربر جاری می‌تواند به ریویو پاسخ دهد
    can_reply = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LawyerReview
        fields = [
            "id", "relation", "lawyer_name", "client_name", 
            "rating", "comment", "short_comment", "reply", 
            "can_reply", "is_approved", "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "lawyer_name", "client_name", "is_approved", 
            "created_at", "updated_at", "short_comment", "can_reply"
        ]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def get_short_comment(self, obj):
        """
        نمایش خلاصه ریویو (تا 50 کاراکتر)
        """
        if obj.comment:
            return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
        return ""

    def get_can_reply(self, obj):
        """
        بررسی اینکه کاربر جاری می‌تواند ریپلای بدهد:
        - فقط اگر کاربر خودش صاحب ریویو باشد
        - یا ادمین/وکیل مجاز
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        user = request.user
        # مالک ریویو یا وکیل مربوطه می‌تواند ریپلای بدهد
        return user == obj.relation.client.user or user == obj.relation.lawyer.user or user.is_staff