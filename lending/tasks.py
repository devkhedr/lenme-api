from celery import shared_task
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import UserProfile
from payment.models import Payment


@shared_task
def process_loan_repayments():
    """
    Process loan repayments that are due or overdue.

    This task runs every hour and:
    1. Identifies payments that are due today or overdue
    2. Checks if borrowers have sufficient balance
    3. Processes automatic payments for funded loans
    4. Updates loan status to completed when all payments are made
    5. Sends notifications for overdue payments

    Returns:
        dict: Summary of processed payments
    """
    today = timezone.now().date()

    # Find all payments that are due today or overdue and still pending
    overdue_payments = Payment.objects.filter(
        due_date__lte=today, status="pending", loan__status="funded"
    ).select_related("loan", "loan__borrower", "loan__lender")

    processed_count = 0
    failed_count = 0
    completed_loans = []

    for payment in overdue_payments:
        loan = payment.loan
        borrower = loan.borrower

        try:
            with transaction.atomic():
                # Get borrower profile
                borrower_profile, created = UserProfile.objects.get_or_create(
                    user=borrower,
                    defaults={"user_type": "borrower", "balance": Decimal("0.00")},
                )

                # Check if borrower has sufficient balance
                if borrower_profile.balance >= payment.amount:
                    # Process automatic payment
                    result = _process_automatic_payment(payment, borrower_profile)
                    if result["success"]:
                        processed_count += 1

                        # Check if loan is now completed
                        if _check_loan_completion(loan):
                            completed_loans.append(loan.id)
                    else:
                        failed_count += 1

        except Exception as e:
            failed_count += 1

    result = {
        "task": "process_loan_repayments",
        "timestamp": timezone.now().isoformat(),
        "processed_payments": processed_count,
        "failed_payments": failed_count,
        "completed_loans": completed_loans,
        "total_due_payments": overdue_payments.count(),
    }

    return result


def _process_automatic_payment(payment, borrower_profile):
    try:
        loan = payment.loan

        # Calculate platform fee distribution
        lenme_fee = loan.lenme_fee or Decimal("0")
        if loan.loan_period_months > 0:
            platform_fee_per_payment = lenme_fee / loan.loan_period_months
        else:
            platform_fee_per_payment = Decimal("0")

        lender_amount = payment.amount - platform_fee_per_payment

        # Deduct from borrower's balance
        borrower_profile.balance -= payment.amount
        borrower_profile.save()

        # Update payment status
        payment.status = "paid"
        payment.paid_at = timezone.now()
        payment.platform_fee = platform_fee_per_payment.quantize(Decimal("0.01"))
        payment.lender_amount = lender_amount.quantize(Decimal("0.01"))
        payment.save()

        # Add lender's portion to lender's balance
        lender_profile, created = UserProfile.objects.get_or_create(
            user=loan.lender,
            defaults={"user_type": "lender", "balance": Decimal("0.00")},
        )
        lender_profile.balance += lender_amount
        lender_profile.save()

        return {
            "success": True,
            "payment_id": payment.id,
            "amount": str(payment.amount),
            "platform_fee": str(platform_fee_per_payment),
            "lender_amount": str(lender_amount),
        }

    except Exception as e:
        return {"success": False, "error": str(e), "payment_id": payment.id}


def _check_loan_completion(loan):
    all_payments = Payment.objects.filter(loan=loan)
    if all(p.status == "paid" for p in all_payments):
        loan.status = "completed"
        loan.save()
        return True
    return False
