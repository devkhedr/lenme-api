from django.db import models
from lending.models import Loan


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="payments")
    payment_number = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    paid_at = models.DateTimeField(null=True, blank=True)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lender_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["payment_number"]

    def __str__(self):
        return (
            f"Payment #{self.payment_number} for Loan #{self.loan.id} - {self.status}"
        )
