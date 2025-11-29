from decimal import Decimal
from django.db import models


class Loan(models.Model):
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    loan_start_date = models.DateField()
    number_of_payments = models.PositiveIntegerField()
    periodicity = models.CharField(max_length=10)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Loan {self.pk}"


class Payment(models.Model):
    loan = models.ForeignKey(Loan, related_name="payments", on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField()
    due_date = models.DateField()
    principal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    interest = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["sequence"]
        unique_together = ("loan", "sequence")

    def __str__(self) -> str:
        return f"Payment {self.sequence} for Loan {self.loan_id}"
