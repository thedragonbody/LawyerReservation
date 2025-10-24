# Generated manually by ChatGPT
from decimal import Decimal

import django.db.models.deletion
from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Wallet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("balance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("reserved_balance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wallet",
                        to="users.user",
                    ),
                ),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="WalletTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("deposit", "Deposit"),
                            ("reserve", "Reserve"),
                            ("release", "Release"),
                            ("debit", "Debit"),
                            ("refund", "Refund"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        validators=[MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "payment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wallet_transactions",
                        to="payments.payment",
                    ),
                ),
                (
                    "wallet",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transactions",
                        to="payments.wallet",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddField(
            model_name="payment",
            name="wallet_reserved_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AlterField(
            model_name="payment",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("idpay", "IDPay"),
                    ("zarinpal", "Zarinpal"),
                    ("wallet", "Wallet"),
                ],
                default="idpay",
                max_length=20,
            ),
        ),
    ]
