from django.utils.translation import gettext_lazy as _
from django.db import models

class AppointmentStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    PAID = 'paid', _('Paid')
    CONFIRMED = 'confirmed', _('Confirmed')
    CANCELLED = 'cancelled', _('Cancelled')

class SessionType(models.TextChoices):
    ONLINE = 'online', _('Online')
    OFFLINE = 'offline', _('Offline')

class CaseResult(models.TextChoices):
    WON = 'won', _('Won')
    LOST = 'lost', _('Lost')
    PENDING = 'pending', _('Pending')