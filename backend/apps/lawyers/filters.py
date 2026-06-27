import django_filters
from django.db import models
from .models import LawyerProfile


class LawyerFilter(django_filters.FilterSet):
    area = django_filters.CharFilter(field_name='practice_areas__area', lookup_expr='exact')
    min_rate = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='gte')
    max_rate = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='lte')
    min_fee = django_filters.NumberFilter(field_name='consultation_fee', lookup_expr='gte')
    max_fee = django_filters.NumberFilter(field_name='consultation_fee', lookup_expr='lte')
    min_experience = django_filters.NumberFilter(field_name='years_experience', lookup_expr='gte')
    min_rating = django_filters.NumberFilter(field_name='average_rating', lookup_expr='gte')
    accepting = django_filters.BooleanFilter(field_name='is_accepting_clients')
    language = django_filters.CharFilter(field_name='languages', lookup_expr='icontains')
    city = django_filters.CharFilter(method='filter_city')

    def filter_city(self, queryset, name, value):
        return queryset.filter(models.Q(city__icontains=value) | models.Q(office_address__icontains=value))

    class Meta:
        model = LawyerProfile
        fields = ['area', 'city', 'min_rate', 'max_rate', 'min_fee', 'max_fee', 'min_experience', 'min_rating', 'accepting']
