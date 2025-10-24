from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_alter_passwordresetcode_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OAuthToken",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        choices=[("google", "Google"), ("microsoft", "Microsoft")],
                        default="google",
                        max_length=50,
                    ),
                ),
                ("access_token", models.TextField()),
                ("refresh_token", models.TextField(blank=True, null=True)),
                ("scope", models.CharField(blank=True, max_length=255)),
                ("token_type", models.CharField(blank=True, max_length=50)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="oauth_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("user", "provider"),
                "unique_together": {("user", "provider")},
            },
        ),
    ]
