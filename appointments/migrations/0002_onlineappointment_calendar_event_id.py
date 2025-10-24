from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="onlineappointment",
            name="calendar_event_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
