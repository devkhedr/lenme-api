from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from .models import Loan, LoanOffer, UserProfile
from .serializers import (
    LoanSerializer,
    LoanOfferSerializer,
    CreateUserSerializer,
)
from payment.models import Payment
from payment.serializers import PaymentSerializer


class CreateUserView(APIView):
    """
    Create a new user with profile.

    Expected input:
    - username: Unique username
    - email: User email
    - password: Password (min 8 characters)
    - first_name: First name
    - last_name: Last name
    - user_type: "borrower" or "lender"
    - balance: Initial balance (optional, default: 0)
    """

    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                profile, created = UserProfile.objects.get_or_create(
                    user=user, defaults={"user_type": "borrower", "balance": 0}
                )
                return Response(
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "profile": {
                            "user_type": profile.user_type,
                            "balance": str(profile.balance),
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                return Response(
                    {"error": "Username already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoanDetailView(APIView):
    """
    Retrieve loan details by ID including payment schedule.

    Returns loan information and associated payments.
    """

    def get(self, request, loan_id):
        try:
            loan = Loan.objects.get(id=loan_id)
        except Loan.DoesNotExist:
            return Response(
                {"error": "Loan not found"}, status=status.HTTP_404_NOT_FOUND
            )

        loan_data = LoanSerializer(loan).data
        payments = Payment.objects.filter(loan=loan)
        payments_data = PaymentSerializer(payments, many=True).data

        return Response({"loan": loan_data, "payments": payments_data})


class CreateLoanView(APIView):
    """
    Create a new loan application.

    Expected input:
    - borrower_id: ID of the borrower
    - loan_amount: Loan amount requested
    - loan_period_months: Loan period in months
    """

    def post(self, request):
        borrower_id = request.data.get("borrower_id")
        loan_amount = request.data.get("loan_amount")
        loan_period_months = request.data.get("loan_period_months")

        if not all([borrower_id, loan_amount, loan_period_months]):
            return Response(
                {
                    "error": "borrower_id, loan_amount, and loan_period_months are required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            borrower = User.objects.get(id=borrower_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Borrower not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Ensure borrower has a profile
        borrower_profile, created = UserProfile.objects.get_or_create(
            user=borrower, defaults={"user_type": "borrower", "balance": 0}
        )

        loan = Loan.objects.create(
            borrower=borrower,
            loan_amount=Decimal(loan_amount),
            loan_period_months=int(loan_period_months),
            status="pending",
        )

        serializer = LoanSerializer(loan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AvailableLoansView(APIView):
    """
    List all available loans that need lenders.

    Returns loans without a lender that are in 'pending' status.
    """

    def get(self, request):
        loans = Loan.objects.filter(lender__isnull=True, status="pending")
        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data)


class SubmitOfferView(APIView):
    """
    Lender submits an offer for a loan.

    Expected input:
    - loan_id: ID of the loan
    - lender_id: ID of the lender
    - annual_interest_rate: Annual interest rate (%)
    """

    def post(self, request):
        loan_id = request.data.get("loan_id")
        lender_id = request.data.get("lender_id")
        annual_interest_rate = request.data.get("annual_interest_rate")

        if not all([loan_id, lender_id, annual_interest_rate]):
            return Response(
                {"error": "loan_id, lender_id, and annual_interest_rate are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            loan = Loan.objects.get(id=loan_id)
            lender = User.objects.get(id=lender_id)
        except (Loan.DoesNotExist, User.DoesNotExist):
            return Response(
                {"error": "Loan or Lender not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Ensure lender has a profile
        lender_profile, created = UserProfile.objects.get_or_create(
            user=lender, defaults={"user_type": "lender", "balance": 0}
        )

        if loan.lender is not None:
            return Response(
                {"error": "Loan already has a lender"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if lender has sufficient balance before allowing offer submission
        lenme_fee = Decimal("3.75")
        required_amount = loan.loan_amount + lenme_fee

        if lender_profile.balance < required_amount:
            return Response(
                {
                    "error": f"Insufficient balance to fund this loan. Required: ${required_amount}, Available: ${lender_profile.balance}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        offer = LoanOffer.objects.create(
            loan=loan, lender=lender, annual_interest_rate=Decimal(annual_interest_rate)
        )

        # Note: Loan remains in "pending" status until offer is accepted and funded

        serializer = LoanOfferSerializer(offer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AcceptOfferView(APIView):
    """
    Borrower accepts a lender's offer.

    Expected input:
    - offer_id: ID of the offer to accept

    This will fund the loan and create payment schedule.
    """

    def post(self, request):
        offer_id = request.data.get("offer_id")

        if not offer_id:
            return Response(
                {"error": "offer_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            offer = LoanOffer.objects.get(id=offer_id)
        except LoanOffer.DoesNotExist:
            return Response(
                {"error": "Offer not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if offer.is_accepted:
            return Response(
                {"error": "Offer already accepted"}, status=status.HTTP_400_BAD_REQUEST
            )

        loan = offer.loan

        # Get or create lender profile
        lender_profile, created = UserProfile.objects.get_or_create(
            user=offer.lender, defaults={"user_type": "lender", "balance": 0}
        )

        # Calculate total loan amount (loan amount + lenme fee)
        lenme_fee = Decimal("3.75")
        total_loan_amount = loan.loan_amount + lenme_fee

        # Check if lender still has sufficient balance (balance might have changed since offer was made)
        if lender_profile.balance < total_loan_amount:
            return Response(
                {
                    "error": f"Lender no longer has sufficient balance to fund this loan."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Deduct from lender's balance
        lender_profile.balance -= total_loan_amount
        lender_profile.save()

        # Update loan
        loan.lender = offer.lender
        loan.annual_interest_rate = offer.annual_interest_rate
        loan.lenme_fee = lenme_fee
        loan.total_loan_amount = total_loan_amount
        loan.status = "funded"
        loan.funded_at = timezone.now()
        loan.save()

        offer.is_accepted = True
        offer.save()

        # Schedule payments
        self._create_payment_schedule(loan)

        serializer = LoanSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _create_payment_schedule(self, loan):
        """Create monthly payment schedule"""
        # Calculate monthly payment amount with interest
        principal = loan.total_loan_amount
        monthly_rate = loan.annual_interest_rate / Decimal("100") / Decimal("12")
        num_payments = loan.loan_period_months

        principal_portion = principal / num_payments
        interest_portion = principal * monthly_rate
        monthly_payment = principal_portion + interest_portion

        monthly_payment = Decimal(str(round(float(monthly_payment), 2)))

        # Create payment records
        for i in range(1, num_payments + 1):
            due_date = (loan.funded_at + relativedelta(months=i)).date()
            Payment.objects.create(
                loan=loan,
                payment_number=i,
                amount=monthly_payment,
                due_date=due_date,
                status="pending",
            )
