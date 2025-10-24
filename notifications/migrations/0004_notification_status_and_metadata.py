from django.db import migrations, models
import django.utils.timezone


def migrate_read_status(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    for notification in Notification.objects.all().only("pk", "is_read"):
        status = "read" if getattr(notification, "is_read", False) else "unread"
        Notification.objects.filter(pk=notification.pk).update(status=status)


def reverse_read_status(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    for notification in Notification.objects.all().only("pk", "status"):
        is_read = getattr(notification, "status", "unread") == "read"
        Notification.objects.filter(pk=notification.pk).update(is_read=is_read)


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_alter_notification_options_remove_notification_link_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="link",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="status",
            field=models.CharField(
                choices=[("unread", "Unread"), ("read", "Read")],
                default="unread",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="notification",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("appointment_confirmed", "Appointment Confirmed"),
                    ("appointment_reminder", "Appointment Reminder"),
                    ("payment_success", "Payment Success"),
                    ("inperson_payment_success", "In-person Payment Success"),
                    ("inperson_payment_refunded", "In-person Payment Refunded"),
                ],
                default="general",
                max_length=50,
            ),
        ),
        migrations.RunPython(migrate_read_status, reverse_code=reverse_read_status),
        migrations.RemoveField(
            model_name="notification",
            name="is_read",
        ),
    ]
