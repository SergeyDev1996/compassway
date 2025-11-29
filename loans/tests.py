from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Loan
from .serializers import get_period_length, quantize_money


class LoanScheduleAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_schedule(self):
        payload = {
            "amount": "1000",
            "loan_start_date": "10-01-2024",
            "number_of_payments": 4,
            "periodicity": "1m",
            "interest_rate": "0.1",
        }
        response = self.client.post(reverse("loan-create"), data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data["schedule"]
        self.assertEqual(len(data), 4)
        self.assertEqual(data[0]["id"], 1)
        self.assertIn("date", data[0])
        self.assertEqual(data[-1]["id"], 4)
        total_principal = sum(Decimal(str(p["principal"])) for p in data)
        self.assertEqual(total_principal, Decimal("1000"))

    def test_accepts_percentage_interest_input(self):
        payload = {
            "amount": "5000",
            "loan_start_date": "2024-01-10",
            "number_of_payments": 5,
            "periodicity": "1m",
            "interest_rate": "100",
        }

        response = self.client.post(reverse("loan-create"), data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["schedule"]), 5)

        loan = Loan.objects.get(pk=response.data["loan_id"])
        self.assertEqual(loan.interest_rate, Decimal("1.0000"))

    def test_reduce_principal_recalculates_interest(self):
        payload = {
            "amount": "1000",
            "loan_start_date": "2024-01-10",
            "number_of_payments": 4,
            "periodicity": "1m",
            "interest_rate": "0.1",
        }
        create_response = self.client.post(
            reverse("loan-create"), data=payload, format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        loan = Loan.objects.get(pk=create_response.data["loan_id"])
        initial_principals = {}
        initial_interests = {}
        for payment in loan.payments.order_by("sequence"):
            initial_principals[payment.sequence] = payment.principal
            initial_interests[payment.sequence] = payment.interest
        payment = loan.payments.get(sequence=2)
        original_principal = payment.principal
        original_interest = payment.interest
        reduction_payload = {"reduction": "50"}
        url = reverse("payment-reduce", args=[loan.pk, payment.sequence])
        response = self.client.post(url, data=reduction_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        reduction = Decimal(reduction_payload["reduction"])
        post_serializer_principal = quantize_money(original_principal - reduction)
        expected_principal = quantize_money(
            max(Decimal("0.00"), post_serializer_principal - reduction)
        )
        self.assertEqual(payment.principal, expected_principal)
        updated_schedule = response.data["schedule"]
        third_payment = loan.payments.get(sequence=3)
        updated_third_interest = Decimal(str(updated_schedule[2]["interest"]))
        self.assertEqual(third_payment.interest, updated_third_interest)
        self.assertNotEqual(third_payment.interest, initial_interests[3])

        rate_per_period = loan.interest_rate * get_period_length(loan.periodicity)
        outstanding = loan.amount
        expected_interests = {}
        for sequence, starting_principal in initial_principals.items():
            principal_for_outstanding = starting_principal
            if sequence == payment.sequence:
                principal_for_outstanding = quantize_money(
                    max(Decimal("0.00"), post_serializer_principal - reduction)
                )

            interest = quantize_money(outstanding * rate_per_period)

            if sequence >= payment.sequence:
                expected_interests[sequence] = interest

            outstanding = quantize_money(
                max(Decimal("0.00"), outstanding - principal_for_outstanding)
            )

        for sequence, expected_interest in expected_interests.items():
            scheduled_payment = loan.payments.get(sequence=sequence)
            self.assertEqual(scheduled_payment.interest, expected_interest)
