from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Payment
from .serializers import PaymentSerializer
from lending.models import Loan


class MakePaymentView(APIView):
    """
    Borrower makes a monthly payment.

    Expected input (either option):
    Option 1: payment_id - ID of the payment to make
    Option 2: loan_id + payment_number - Loan ID and payment number
    """

    def post(self, request):
        payment_id = request.data.get("payment_id")
        loan_id = request.data.get("loan_id")
        payment_number = request.data.get("payment_number")

        # Allow payment by either payment_id or loan_id + payment_number
        if payment_id:
            try:
                payment = Payment.objects.get(id=payment_id)
            except Payment.DoesNotExist:
                return Response(
                    {"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND
                )
        elif loan_id and payment_number:
            try:
                payment = Payment.objects.get(
                    loan_id=loan_id, payment_number=payment_number
                )
            except Payment.DoesNotExist:
                return Response(
                    {"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {
                    "error": "Either payment_id or (loan_id and payment_number) are required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.status == "paid":
            return Response(
                {"error": "Payment already made"}, status=status.HTTP_400_BAD_REQUEST
            )

        loan = payment.loan

        # Calculate platform fee from this payment
        # Platform gets a percentage of each payment based on the original lenme fee
        from decimal import Decimal

        # Calculate what percentage of total payments this represents
        total_loan_amount = loan.loan_amount
        lenme_fee = loan.lenme_fee or Decimal("0")  # Default to 0 if no fee set

        # Calculate platform share from this payment
        # Platform fee is distributed across all payments proportionally
        if loan.loan_period_months > 0:
            platform_fee_per_payment = lenme_fee / loan.loan_period_months
        else:
            platform_fee_per_payment = Decimal("0")

        lender_amount = payment.amount - platform_fee_per_payment

        # Update payment status and save breakdown
        payment.status = "paid"
        payment.paid_at = timezone.now()
        payment.platform_fee = platform_fee_per_payment.quantize(Decimal("0.01"))
        payment.lender_amount = lender_amount.quantize(Decimal("0.01"))
        payment.save()

        # Add lender's portion to lender's balance
        # Get or create lender profile
        from lending.models import UserProfile

        lender_profile, created = UserProfile.objects.get_or_create(
            user=loan.lender, defaults={"user_type": "lender", "balance": 0}
        )
        lender_profile.balance += lender_amount
        lender_profile.save()

        # Check if all payments are completed
        all_payments = Payment.objects.filter(loan=loan)
        if all(p.status == "paid" for p in all_payments):
            loan.status = "completed"
            loan.save()

        serializer = PaymentSerializer(payment)
        return Response(
            {
                "payment": serializer.data,
                "loan_status": loan.status,
                "payment_breakdown": {
                    "total_payment": str(payment.amount),
                    "platform_fee": str(
                        platform_fee_per_payment.quantize(Decimal("0.01"))
                    ),
                    "lender_amount": str(lender_amount.quantize(Decimal("0.01"))),
                },
                "lender_new_balance": str(lender_profile.balance),
            },
            status=status.HTTP_200_OK,
        )


class LoanPaymentsView(APIView):
    """
    Get all payments for a specific loan.

    Returns all payments (both paid and pending) for the loan.
    """

    def get(self, request, loan_id):
        try:
            loan = Loan.objects.get(id=loan_id)
        except Loan.DoesNotExist:
            return Response(
                {"error": "Loan not found"}, status=status.HTTP_404_NOT_FOUND
            )

        payments = Payment.objects.filter(loan=loan)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)
