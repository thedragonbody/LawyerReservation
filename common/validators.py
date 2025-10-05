from django.core.exceptions import ValidationError
from common.choices import CaseResult

def validate_slot_time(start_time, end_time):
    if end_time <= start_time:
        raise ValidationError("end_time must be after start_time.")

def validate_case_end_date(result, end_date):
    if result in [CaseResult.WON, CaseResult.LOST] and not end_date:
        raise ValidationError("end_date is required if case result is won or lost.")