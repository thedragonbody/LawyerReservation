from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0003_inpersonappointment"),
        ("payments", "0002_wallet"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="inperson_appointment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="appointments.inpersonappointment",
            ),
        ),
    ]
