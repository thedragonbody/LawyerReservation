import os
from collections import defaultdict
from typing import Dict, Iterable, List

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Report presence of critical environment variables for external integrations."

    def handle(self, *args, **options):
        requirements = self._build_requirements()
        grouped: Dict[str, List[str]] = defaultdict(list)
        missing_required = False

        for requirement in requirements:
            group = requirement["group"]
            key = requirement["key"]
            note = requirement["note"]
            required_flag = self._is_required(requirement)
            value = os.environ.get(key)

            if required_flag and not value:
                missing_required = True
                grouped[group].append(self.style.ERROR(f"✗ {key}: missing ({note})"))
            elif value:
                grouped[group].append(self.style.SUCCESS(f"✓ {key}: set"))
            else:
                grouped[group].append(self.style.WARNING(f"• {key}: optional ({note})"))

        for group, lines in grouped.items():
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(group))
            for line in lines:
                self.stdout.write(f"  {line}")

        if missing_required:
            raise CommandError("Missing required environment variables. See messages above.")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("All required environment variables are set."))

    def _build_requirements(self) -> Iterable[Dict[str, object]]:
        return [
            {"group": "Core", "key": "SECRET_KEY", "note": "Django crypto key", "required": True},
            {
                "group": "Database",
                "key": "DB_NAME",
                "note": "Primary PostgreSQL database name",
                "required": True,
            },
            {
                "group": "Database",
                "key": "DB_USER",
                "note": "Database username",
                "required": True,
            },
            {
                "group": "Database",
                "key": "DB_PASSWORD",
                "note": "Database password",
                "required": True,
            },
            {
                "group": "Payments",
                "key": "IDPAY_API_KEY",
                "note": "IDPay API key for payment gateway",
                "required": True,
            },
            {
                "group": "Payments",
                "key": "IDPAY_API_URL",
                "note": "Override for the IDPay API base URL",
                "required": False,
            },
            {
                "group": "Payments",
                "key": "IDPAY_SANDBOX",
                "note": "Set to 1 to enable IDPay sandbox",
                "required": False,
            },
            {
                "group": "SMS",
                "key": "SMS_API_KEY",
                "note": "API key for the configured SMS provider",
                "required": self._sms_key_required,
            },
            {
                "group": "SMS",
                "key": "SMS_SENDER",
                "note": "Registered sender number for SMS",
                "required": False,
            },
            {
                "group": "Email",
                "key": "EMAIL_HOST",
                "note": "SMTP host for outgoing mail",
                "required": self._email_required,
            },
            {
                "group": "Email",
                "key": "EMAIL_PORT",
                "note": "SMTP port (465/587)",
                "required": self._email_required,
            },
            {
                "group": "Email",
                "key": "EMAIL_HOST_USER",
                "note": "SMTP username (from address)",
                "required": self._email_required,
            },
            {
                "group": "Email",
                "key": "EMAIL_HOST_PASSWORD",
                "note": "SMTP password or app password",
                "required": self._email_required,
            },
            {
                "group": "Email",
                "key": "DEFAULT_FROM_EMAIL",
                "note": "Default sender email",
                "required": False,
            },
            {
                "group": "AI",
                "key": "OPENAI_API_KEY",
                "note": "API key for AI assistant features",
                "required": False,
            },
            {
                "group": "Caching",
                "key": "REDIS_URL",
                "note": "Redis URL for cache & Celery broker",
                "required": False,
            },
        ]

    def _is_required(self, requirement: Dict[str, object]) -> bool:
        flag = requirement.get("required", False)
        if callable(flag):
            return bool(flag())
        return bool(flag)

    def _sms_key_required(self) -> bool:
        return getattr(settings, "SMS_PROVIDER", "console") != "console"

    def _email_required(self) -> bool:
        return settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend'
