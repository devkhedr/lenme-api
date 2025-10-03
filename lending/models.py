from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    user_type = models.CharField(
        max_length=10, choices=[("borrower", "Borrower"), ("lender", "Lender")]
    )

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"


class Loan(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("funded", "Funded"),
        ("completed", "Completed"),
    ]

    borrower = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="loans_as_borrower"
    )
    lender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="loans_as_lender",
        null=True,
        blank=True,
    )
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    loan_period_months = models.IntegerField()
    annual_interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    lenme_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_loan_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    funded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Loan #{self.id} - ${self.loan_amount} - {self.status}"


class LoanOffer(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="offers")
    lender = models.ForeignKey(User, on_delete=models.CASCADE)
    annual_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Offer for Loan #{self.loan.id} by {self.lender.username}"
