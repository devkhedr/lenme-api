from django.urls import path
from .views import (
    AvailableLoansView,
    SubmitOfferView,
    AcceptOfferView,
    LoanDetailView,
    CreateLoanView,
    CreateUserView,
)

urlpatterns = [
    path("user/", CreateUserView.as_view(), name="create-user"),
    path("loan/<int:loan_id>/", LoanDetailView.as_view(), name="loan-detail"),
    path("loan/", CreateLoanView.as_view(), name="create-loan"),
    path("loan-list/", AvailableLoansView.as_view(), name="available-loans"),
    path("offers/submit/", SubmitOfferView.as_view(), name="submit-offer"),
    path("offers/accept/", AcceptOfferView.as_view(), name="accept-offer"),
]
