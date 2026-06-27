from rest_framework import serializers
from .models import LawyerProfile, PracticeArea, Education, Availability, Review
from apps.accounts.serializers import UserSerializer


class PracticeAreaSerializer(serializers.ModelSerializer):
    area_display = serializers.CharField(source='get_area_display', read_only=True)

    class Meta:
        model = PracticeArea
        fields = ('id', 'area', 'area_display', 'is_primary')


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ('id', 'institution', 'degree', 'year_graduated')


class AvailabilitySerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = Availability
        fields = ('id', 'date', 'is_closed', 'day_of_week', 'day_display', 'start_time', 'end_time', 'slot_duration_minutes')


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ('id', 'rating', 'comment', 'is_anonymous', 'customer_name', 'created_at')

    def get_customer_name(self, obj):
        if obj.is_anonymous or not obj.customer:
            return 'Anonymous Client'
        return obj.customer.full_name


class LawyerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing/search results."""
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    bar_document_url = serializers.SerializerMethodField()
    primary_area = serializers.SerializerMethodField()
    first_available_slot = serializers.SerializerMethodField()
    smart_badges = serializers.SerializerMethodField()
    practice_areas = PracticeAreaSerializer(many=True, read_only=True)

    class Meta:
        model = LawyerProfile
        fields = (
            'id', 'full_name', 'avatar_url', 'bar_document_url', 'bar_number', 'headline',
            'years_experience', 'hourly_rate', 'consultation_fee', 'city',
            'average_rating', 'total_reviews', 'total_bookings',
            'is_accepting_clients', 'is_featured', 'verification_status',
            'primary_area', 'practice_areas', 'first_available_slot', 'smart_badges',
        )

    def get_avatar_url(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None

    def get_bar_document_url(self, obj):
        if getattr(obj, 'bar_document', None):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.bar_document.url)
            return obj.bar_document.url
        return None


    def get_first_available_slot(self, obj):
        """Lightweight badge value for list card. Real slot logic remains in booking endpoint."""
        from datetime import timedelta, datetime
        from django.utils import timezone
        from .models import Availability
        today = timezone.localdate()
        for offset in range(0, 14):
            day = today + timedelta(days=offset)
            exact = Availability.objects.filter(lawyer=obj, date=day).order_by('start_time')
            if exact.exists():
                if exact.filter(is_closed=True).exists():
                    continue
                av = exact.filter(is_closed=False).first()
            else:
                day_abbr = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][day.weekday()]
                av = Availability.objects.filter(lawyer=obj, day_of_week=day_abbr, is_closed=False).order_by('start_time').first()
            if av:
                return {
                    'date': day.isoformat(),
                    'time': av.start_time.strftime('%H:%M'),
                    'display': f"{day.strftime('%m/%d')} ساعت {av.start_time.strftime('%H:%M')}",
                    'is_today': offset == 0,
                }
        return None

    def get_smart_badges(self, obj):
        first_slot = self.get_first_available_slot(obj)

        if first_slot and first_slot.get('is_today'):
            return ['دارای وقت آزاد امروز']
        if obj.is_featured:
            return ['منتخب لکسارا']
        if obj.total_bookings and obj.total_bookings >= 5:
            return ['پررزرو']
        if obj.average_rating and float(obj.average_rating) >= 4:
            return ['پاسخ‌گو در کمتر از ۲ ساعت']
        return ['فعال امروز']


    def get_primary_area(self, obj):
        pa = obj.practice_areas.filter(is_primary=True).first()
        return pa.get_area_display() if pa else None


class LawyerDetailSerializer(LawyerListSerializer):
    """Full details for a single lawyer page."""
    my_review = serializers.SerializerMethodField()
    education = EducationSerializer(many=True, read_only=True)
    availability = AvailabilitySerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta(LawyerListSerializer.Meta):
        fields = LawyerListSerializer.Meta.fields + (
            'bar_document', 'bio', 'languages', 'office_address',
            'website', 'linkedin', 'phone',
            'education', 'availability', 'reviews', 'my_review',
        )

    def get_my_review(self, obj):
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None) or not request.user.is_authenticated:
            return None
        review = obj.reviews.filter(customer=request.user).first()
        if not review:
            return None
        return ReviewSerializer(review, context=self.context).data


class LawyerProfileUpdateSerializer(serializers.ModelSerializer):
    office_address = serializers.CharField(required=False, allow_blank=True)
    practice_areas = PracticeAreaSerializer(many=True, required=False)
    education = EducationSerializer(many=True, required=False)
    availability = AvailabilitySerializer(many=True, required=False)

    class Meta:
        model = LawyerProfile
        fields = (
            'bar_number', 'bar_document', 'headline', 'bio', 'years_experience',
            'hourly_rate', 'consultation_fee', 'languages',
            'city', 'office_address', 'website', 'linkedin',
            'is_accepting_clients', 'practice_areas', 'education', 'availability',
        )

    def validate(self, attrs):
        bar_number = attrs.get('bar_number', getattr(self.instance, 'bar_number', ''))
        bar_document = attrs.get('bar_document', getattr(self.instance, 'bar_document', None))
        if not bar_number or str(bar_number).startswith('PENDING'):
            raise serializers.ValidationError({'bar_number': 'شماره پروانه وکالت الزامی است.'})
        if not bar_document:
            raise serializers.ValidationError({'bar_document': 'بارگذاری فایل پروانه وکالت الزامی است.'})
        return attrs

    def update(self, instance, validated_data):
        practice_areas = validated_data.pop('practice_areas', None)
        education_data = validated_data.pop('education', None)
        availability_data = validated_data.pop('availability', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if practice_areas is not None:
            instance.practice_areas.all().delete()
            for pa in practice_areas:
                PracticeArea.objects.create(lawyer=instance, **pa)

        if education_data is not None:
            instance.education.all().delete()
            for edu in education_data:
                Education.objects.create(lawyer=instance, **edu)

        if availability_data is not None:
            instance.availability.all().delete()
            for avail in availability_data:
                Availability.objects.create(lawyer=instance, **avail)

        return instance


class CreateReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('rating', 'comment', 'is_anonymous')

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value
