from django.db import models
from django.conf import settings
import uuid


PRACTICE_AREAS = [
    ('corporate', 'Corporate Law'),
    ('criminal', 'Criminal Defense'),
    ('family', 'Family Law'),
    ('immigration', 'Immigration'),
    ('intellectual_property', 'Intellectual Property'),
    ('real_estate', 'Real Estate'),
    ('employment', 'Employment Law'),
    ('tax', 'Tax Law'),
    ('personal_injury', 'Personal Injury'),
    ('bankruptcy', 'Bankruptcy'),
    ('civil_litigation', 'Civil Litigation'),
    ('estate_planning', 'Estate Planning'),
    ('healthcare', 'Healthcare Law'),
    ('environmental', 'Environmental Law'),
    ('international', 'International Law'),
]

DAYS_OF_WEEK = [
    ('mon', 'Monday'),
    ('tue', 'Tuesday'),
    ('wed', 'Wednesday'),
    ('thu', 'Thursday'),
    ('fri', 'Friday'),
    ('sat', 'Saturday'),
    ('sun', 'Sunday'),
]


class LawyerProfile(models.Model):
    VERIFICATION_STATUS = [
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lawyer_profile',
        limit_choices_to={'role': 'lawyer'},
    )
    bar_number = models.CharField(max_length=50, unique=True)
    bar_document = models.FileField(upload_to='lawyer_licenses/', blank=True, null=True)
    headline = models.CharField(max_length=200, blank=True, help_text="E.g. 'Senior Partner at Smith & Associates'")
    bio = models.TextField(blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           help_text='Fee for initial 30-min consultation')
    languages = models.JSONField(default=list, blank=True)  # ["English", "Spanish"]
    city = models.CharField(max_length=100, blank=True)
    office_address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)

    # Status
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS, default='pending')
    is_accepting_clients = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Stats (denormalized for performance)
    total_reviews = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_bookings = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lawyer_profiles'

    def __str__(self):
        return f'Lawyer: {self.user.full_name}'


class PracticeArea(models.Model):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='practice_areas')
    area = models.CharField(max_length=50, choices=PRACTICE_AREAS)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = 'lawyer_practice_areas'
        unique_together = ('lawyer', 'area')

    def __str__(self):
        return f'{self.lawyer.user.full_name} — {self.get_area_display()}'


class Education(models.Model):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='education')
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    year_graduated = models.PositiveIntegerField()

    class Meta:
        db_table = 'lawyer_education'
        ordering = ['-year_graduated']


class Availability(models.Model):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='availability')
    # For default weekly schedule use day_of_week. For exact day overrides use date.
    date = models.DateField(blank=True, null=True)
    is_closed = models.BooleanField(default=False)
    day_of_week = models.CharField(max_length=3, choices=DAYS_OF_WEEK, blank=True, null=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.PositiveIntegerField(default=60)

    class Meta:
        db_table = 'lawyer_availability'
        ordering = ['date', 'day_of_week', 'start_time']

    def __str__(self):
        label = self.date or self.get_day_of_week_display()
        return f'{self.lawyer.user.full_name} — {label} {self.start_time}–{self.end_time}'


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='given_reviews',
    )
    rating = models.PositiveSmallIntegerField()   # 1–5
    comment = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lawyer_reviews'
        ordering = ['-created_at']
