from django.urls import path
from .views import MakePaymentView, LoanPaymentsView

urlpatterns = [
    path("make/", MakePaymentView.as_view(), name="make-payment"),
    path("loan/<int:loan_id>/", LoanPaymentsView.as_view(), name="loan-payments"),
]
