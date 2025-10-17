from rest_framework import serializers
from .models import LawyerReview
from appointments.models import Appointment

class LawyerReviewSerializer(serializers.ModelSerializer):
    lawyer_name = serializers.CharField(source="relation.lawyer.user.get_full_name", read_only=True)
    client_name = serializers.CharField(source="relation.client.user.get_full_name", read_only=True)
    short_comment = serializers.SerializerMethodField(read_only=True)
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

    def validate_relation(self, value):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated.")

        # فقط client می‌تواند برای relation خودش review ایجاد کند
        if request.user != value.client.user:
            raise serializers.ValidationError("You can only review your own appointments/lawyers.")

        # بررسی اینکه فقط یک review برای هر relation موجود باشد
        if LawyerReview.objects.filter(relation=value).exists():
            raise serializers.ValidationError("You have already reviewed this relation.")

        # (اختیاری) بررسی اینکه client حداقل یک appointment تایید شده با وکیل داشته باشد
        if not Appointment.objects.filter(client=value.client, lawyer=value.lawyer, status="completed").exists():
            raise serializers.ValidationError("You can only review after completing an appointment with this lawyer.")

        return value

    def get_short_comment(self, obj):
        if obj.comment:
            return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
        return ""

    def get_can_reply(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        user = request.user
        return user == obj.relation.client.user or user == obj.relation.lawyer.user or user.is_staff
    
    def get_queryset(self):
        user = self.request.user
        qs = LawyerReview.objects.select_related(
            "relation",
            "relation__lawyer",
            "relation__lawyer__user",
            "relation__client",
            "relation__client__user"
        ).order_by("-created_at")
        
        if user.is_authenticated and not user.is_staff:
            qs = qs.filter(is_approved=True)
        return qs