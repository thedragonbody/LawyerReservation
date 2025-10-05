from rest_framework import serializers
from .models import Case, CaseComment

class CaseCommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    replies = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = CaseComment
        fields = ['id', 'case', 'user', 'content', 'parent', 'replies', 'created_at', 'can_edit', 'can_delete']
        read_only_fields = ['id', 'user', 'case', 'created_at', 'parent']

    def get_replies(self, obj):
        return CaseCommentSerializer(obj.replies.all(), many=True, context=self.context).data

    def get_can_edit(self, obj):
        user = self.context['request'].user
        return obj.user == user

    def get_can_delete(self, obj):
        user = self.context['request'].user
        is_comment_owner = obj.user == user
        is_case_lawyer = hasattr(user, "lawyer_profile") and obj.case.lawyer == user.lawyer_profile
        return is_comment_owner or is_case_lawyer


class CaseSerializer(serializers.ModelSerializer):
    lawyer = serializers.StringRelatedField()
    comments = CaseCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Case
        fields = ["id", "lawyer", "title", "description", "file", "result",
                  "start_date", "end_date", "is_public", "created_at", "comments"]
    def validate(self, data):
        result = data.get("result")
        end_date = data.get("end_date")
        if result in ["won", "lost"] and not end_date:
            raise serializers.ValidationError({"end_date": "End date must be set when result is won or lost."})
        return data