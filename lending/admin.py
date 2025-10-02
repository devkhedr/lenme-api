from django.contrib import admin
from .models import UserProfile, Loan, LoanOffer


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "user_type", "balance"]
    list_filter = ["user_type"]


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["id", "borrower", "lender", "loan_amount", "status", "created_at"]
    list_filter = ["status"]


@admin.register(LoanOffer)
class LoanOfferAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "loan",
        "lender",
        "annual_interest_rate",
        "is_accepted",
        "created_at",
    ]
    list_filter = ["is_accepted"]
