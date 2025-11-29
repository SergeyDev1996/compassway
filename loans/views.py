from decimal import Decimal

from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from .models import Loan, Payment
from .serializers import LoanCreateSerializer, PaymentAdjustmentSerializer, PaymentSerializer
from .services import (
    adjust_payment,
    get_period_length,
    next_due_date,
    quantize_money,
)


class LoanScheduleCreateView(generics.CreateAPIView):
    serializer_class = LoanCreateSerializer


    def calculate_emi(self, loan):
        P = Decimal(loan.amount)
        r = Decimal(loan.interest_rate)
        n = loan.number_of_payments

        l = get_period_length(loan.periodicity)
        i = r * l  # per-period interest

        if i == 0:
            return quantize_money(P / n)

        emi = i * P / (1 - (1 + i) ** Decimal(-n))
        return quantize_money(emi)

    def create_payments(self, loan: Loan):
        principal_remaining = Decimal(loan.amount)
        start_date = loan.loan_start_date
        payments = []

        emi = self.calculate_emi(loan)
        l = get_period_length(loan.periodicity)
        current_delta = next_due_date(loan.periodicity)
        for idx in range(1, loan.number_of_payments + 1):

            current_date = start_date + current_delta
            start_date = current_date
            i = Decimal(loan.interest_rate) * l
            interest = quantize_money(principal_remaining * i)

            principal = quantize_money(emi - interest)

            if idx == loan.number_of_payments:
                principal = quantize_money(principal_remaining)
                emi = quantize_money(principal + interest)

            payments.append(
                Payment(
                    loan=loan,
                    sequence=idx,
                    due_date=current_date,
                    principal=principal,
                    interest=interest,
                )
            )

            principal_remaining -= principal

        Payment.objects.bulk_create(payments)

    def perform_create(self, serializer):
        with transaction.atomic():
            loan = Loan.objects.create(**serializer.validated_data)
            self.create_payments(loan)
        return loan

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        loan = self.perform_create(serializer)
        schedule = PaymentSerializer(loan.payments.all(), many=True)
        return Response(
            {"loan_id": loan.id, "schedule": schedule.data},
            status=status.HTTP_201_CREATED,
        )


class PaymentAdjustmentView(generics.GenericAPIView):
    serializer_class = PaymentAdjustmentSerializer

    def get_payment(self, loan_id: int, sequence: int) -> Payment:
        try:
            return Payment.objects.select_related("loan").get(
                loan_id=loan_id, sequence=sequence
            )
        except Payment.DoesNotExist as exc:
            raise NotFound("Payment not found for provided identifiers") from exc

    def post(self, request, loan_id: int, sequence: int, *args, **kwargs):
        payment = self.get_payment(loan_id, sequence)
        serializer = self.get_serializer(data=request.data, context={"payment": payment})
        serializer.is_valid(raise_exception=True)
        adjust_payment(payment, serializer.validated_data["reduction"])
        schedule = PaymentSerializer(payment.loan.payments.all(), many=True)
        return Response(
            {"loan_id": payment.loan_id, "schedule": schedule.data},
            status=status.HTTP_200_OK,
        )
