from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0001_initial"),  # <- اینجا 0001_initial اضافه شد
    ]

    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;"
        )
    ]