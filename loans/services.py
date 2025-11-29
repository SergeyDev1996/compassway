from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple

from dateutil.relativedelta import relativedelta
from django.db import transaction
from rest_framework import serializers

from .models import Payment


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_periodicity(value: str) -> Tuple[int, str]:
    if not value or len(value) < 2:
        raise serializers.ValidationError("Invalid periodicity format.")
    count_part, unit = value[:-1], value[-1]
    if not count_part.isdigit() or unit not in {"d", "w", "m", "y"}:
        raise serializers.ValidationError(
            "Periodicity must follow pattern like '1d', '2w', or '3m'."
        )
    count = int(count_part)
    if count <= 0:
        raise serializers.ValidationError("Periodicity count must be positive.")
    return count, unit


def get_period_length(value: str) -> Decimal:
    """Return the fraction of a year represented by the periodicity value."""

    count, unit = parse_periodicity(value)
    count = Decimal(count)

    if unit == "d":
        return count / Decimal(365)
    if unit == "w":
        return count / Decimal(52)
    if unit == "m":
        return count / Decimal(12)
    if unit == "y":
        return count

    raise ValueError("Unsupported periodicity unit")


def next_due_date(periodicity: str):
    total_count, unit = parse_periodicity(periodicity)
    if unit == "d":
        delta = relativedelta(days=total_count)
    if unit == "w":
        delta = relativedelta(weeks=total_count)
    if unit == "m":
        delta = relativedelta(months=total_count)
    if unit == "y":
        delta = relativedelta(years=total_count)
    return delta


def recalculate_interests(changed_payment: Payment, reduction: Decimal):
    loan = changed_payment.loan
    payments = list(loan.payments.select_for_update().order_by("sequence"))

    # fraction of a year per period
    l = get_period_length(loan.periodicity)
    rate_per_period = loan.interest_rate * l

    outstanding = loan.amount

    for payment in payments:

        # Reduce principal on the changed payment
        if payment.sequence == changed_payment.sequence:
            new_principal = max(Decimal("0.00"), payment.principal - reduction)
            payment.principal = quantize_money(new_principal)
            payment.save(update_fields=["principal"])

        # Compute interest on current outstanding
        interest = quantize_money(outstanding * rate_per_period)

        # Update interest for changed and subsequent payments
        if payment.sequence >= changed_payment.sequence:
            payment.interest = interest
            payment.save(update_fields=["interest"])

        # Decrease outstanding by THIS payment's (possibly updated) principal
        outstanding = max(Decimal("0.00"), outstanding - payment.principal)


def adjust_payment(payment: Payment, reduction: Decimal) -> Payment:
    with transaction.atomic():
        payment.principal = quantize_money(payment.principal - reduction)
        payment.save(update_fields=["principal"])
        recalculate_interests(payment, reduction)
    return payment
