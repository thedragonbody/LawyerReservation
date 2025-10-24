from django.db import migrations

import common.fields


def encrypt_existing_tokens(apps, schema_editor):
    OAuthToken = apps.get_model("users", "OAuthToken")
    for token in OAuthToken.objects.all():
        updated_fields = []
        if token.access_token:
            raw_access = token.access_token
            token.access_token = raw_access
            updated_fields.append("access_token")
        if token.refresh_token:
            raw_refresh = token.refresh_token
            token.refresh_token = raw_refresh
            updated_fields.append("refresh_token")
        if updated_fields:
            token.save(update_fields=updated_fields)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_oauthtoken"),
    ]

    operations = [
        migrations.AlterField(
            model_name="oauthtoken",
            name="access_token",
            field=common.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name="oauthtoken",
            name="refresh_token",
            field=common.fields.EncryptedTextField(blank=True, null=True),
        ),
        migrations.RunPython(encrypt_existing_tokens, reverse_code=noop),
    ]
