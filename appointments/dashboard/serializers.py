from decimal import Decimal

from rest_framework import serializers

from appointments.models import OnlineAppointment


class ClientAppointmentSerializer(serializers.ModelSerializer):
    lawyer_name = serializers.CharField(source="lawyer.user.get_full_name", read_only=True)
    slot_time = serializers.DateTimeField(source="slot.start_time", read_only=True)
    session_type = serializers.SerializerMethodField()

    class Meta:
        model = OnlineAppointment
        fields = [
            "id",
            "lawyer_name",
            "slot_time",
            "status",
            "session_type",
        ]

    def get_session_type(self, obj):
        return getattr(obj, "session_type", None)


class LawyerAppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.user.get_full_name", read_only=True)
    slot_time = serializers.DateTimeField(source="slot.start_time", read_only=True)
    session_type = serializers.SerializerMethodField()

    class Meta:
        model = OnlineAppointment
        fields = [
            "id",
            "client_name",
            "slot_time",
            "status",
            "session_type",
        ]

    def get_session_type(self, obj):
        return getattr(obj, "session_type", None)


class DashboardPerformerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    appointments = serializers.IntegerField()
    success_percent = serializers.FloatField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class StatusCountSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class DashboardMetricsSerializer(serializers.Serializer):
    total_appointments = serializers.IntegerField()
    status_counts = StatusCountSerializer(many=True)
    status_percent = serializers.DictField(child=serializers.FloatField())
    daily_appointments = serializers.DictField(child=serializers.IntegerField())
    daily_revenue = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )
    top_lawyers = DashboardPerformerSerializer(many=True)
    top_clients = DashboardPerformerSerializer(many=True)
    monthly_income = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )
    monthly_sessions = serializers.DictField(child=serializers.IntegerField())
    monthly_tax = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )
    annual_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    annual_tax = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_payments = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_refunds = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_status_counts = serializers.DictField(child=serializers.IntegerField())
    conversion_rate = serializers.FloatField()
    average_ticket_size = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_rating = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()

    def to_representation(self, instance):
        data = super().to_representation(instance)

        decimal_fields = {
            "daily_revenue": True,
            "monthly_income": True,
            "monthly_tax": True,
            "annual_income": False,
            "annual_tax": False,
            "total_payments": False,
            "total_refunds": False,
            "average_ticket_size": False,
        }

        def _normalize(value):
            if isinstance(value, Decimal):
                return value.quantize(Decimal("0.01"))
            return Decimal(str(value)).quantize(Decimal("0.01"))

        for field, is_mapping in decimal_fields.items():
            if field not in data:
                continue
            if is_mapping and isinstance(data[field], dict):
                data[field] = {key: _normalize(val) for key, val in data[field].items()}
            else:
                data[field] = _normalize(data[field])

        for collection in ("top_lawyers", "top_clients"):
            if collection in data:
                for item in data[collection]:
                    item["total_revenue"] = _normalize(item["total_revenue"])

        return data

