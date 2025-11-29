from django.urls import path

from .views import LoanScheduleCreateView, PaymentAdjustmentView

urlpatterns = [
    path("loans/", LoanScheduleCreateView.as_view(), name="loan-create"),
    path(
        "loans/<int:loan_id>/payments/<int:sequence>/reduce/",
        PaymentAdjustmentView.as_view(),
        name="payment-reduce",
    ),
]
