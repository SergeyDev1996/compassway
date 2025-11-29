from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from .models import Payment
from .services import parse_periodicity


class PaymentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="sequence")
    date = serializers.DateField(source="due_date")

    class Meta:
        model = Payment
        fields = ["id", "date", "principal", "interest"]


class LoanCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    loan_start_date = serializers.DateField(
        input_formats=["%Y-%m-%d", "%d-%m-%Y"]
    )
    number_of_payments = serializers.IntegerField(min_value=1)
    periodicity = serializers.CharField()
    interest_rate = serializers.DecimalField(max_digits=7, decimal_places=4)

    def validate_periodicity(self, value: str) -> str:
        parse_periodicity(value)
        return value

    def validate_loan_start_date(self, value):
        return value

    def validate_interest_rate(self, value: Decimal) -> Decimal:
        """Support both fractional and percentage interest inputs."""

        if value > 1:
            value = value / Decimal(100)

        return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


class PaymentAdjustmentSerializer(serializers.Serializer):
    reduction = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)

    def validate(self, attrs):
        payment: Payment = self.context["payment"]
        reduction = attrs["reduction"]
        if reduction > payment.principal:
            raise serializers.ValidationError(
                {"reduction": "Reduction cannot exceed current principal."}
            )
        return attrs
