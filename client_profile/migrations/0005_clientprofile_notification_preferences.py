from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("client_profile", "0004_delete_device"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientprofile",
            name="receive_push_notifications",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="clientprofile",
            name="receive_sms_notifications",
            field=models.BooleanField(default=True),
        ),
    ]
