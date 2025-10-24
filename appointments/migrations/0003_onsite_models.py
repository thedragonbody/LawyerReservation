# Generated manually to add onsite appointment models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("client_profile", "0004_delete_device"),
        ("lawyer_profile", "0003_remove_lawyerprofile_document_and_more"),
        ("appointments", "0002_onlineappointment_calendar_event_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="OnsiteSlot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                ("office_address", models.CharField(blank=True, max_length=255)),
                (
                    "office_latitude",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
                ),
                (
                    "office_longitude",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
                ),
                ("is_booked", models.BooleanField(default=False)),
                (
                    "lawyer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="onsite_slots",
                        to="lawyer_profile.lawyerprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["start_time"],
                "unique_together": {("lawyer", "start_time", "end_time")},
            },
        ),
        migrations.CreateModel(
            name="OnsiteAppointment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("paid", "Paid"),
                            ("confirmed", "Confirmed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("office_address", models.CharField(blank=True, max_length=255)),
                (
                    "office_latitude",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
                ),
                (
                    "office_longitude",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
                ),
                ("notes", models.TextField(blank=True)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="onsite_appointments",
                        to="client_profile.clientprofile",
                    ),
                ),
                (
                    "lawyer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="onsite_appointments",
                        to="lawyer_profile.lawyerprofile",
                    ),
                ),
                (
                    "slot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="appointments",
                        to="appointments.onsiteslot",
                    ),
                ),
            ],
            options={"ordering": ["slot__start_time"]},
        ),
    ]
