import pytest
from django.contrib.auth.models import User
from rest_framework import status
from decimal import Decimal
from lending.models import Loan, LoanOffer
from payment.models import Payment
from django.utils import timezone
from conftest import lending_url


@pytest.mark.django_db
class TestUserCreation:
    """Test user creation and profile setup"""

    def test_create_borrower_user(self, api_client):
        """Test creating a borrower user with profile"""
        user_data = {
            "username": "new_borrower",
            "email": "newborrower@test.com",
            "password": "securepass123",
            "first_name": "John",
            "last_name": "Doe",
            "user_type": "borrower",
            "balance": "1000.00",
        }

        response = api_client.post(lending_url("user/"), user_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["username"] == "new_borrower"
        assert response.data["profile"]["user_type"] == "borrower"
        assert "balance" in response.data["profile"]

        # Verify user and profile were created
        user = User.objects.get(username="new_borrower")
        assert hasattr(user, "profile")
        assert user.profile.user_type == "borrower"

    def test_create_lender_user(self, api_client):
        """Test creating a lender user with profile"""
        user_data = {
            "username": "new_lender",
            "email": "newlender@test.com",
            "password": "securepass123",
            "first_name": "Jane",
            "last_name": "Smith",
            "user_type": "lender",
            "balance": "5000.00",
        }

        response = api_client.post("/api/lending/user/", user_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["username"] == "new_lender"
        assert (
            response.data["profile"]["user_type"] == "lender"
        )  # Uses the provided user_type

    def test_create_user_duplicate_username(self, api_client, borrower_user):
        """Test creating user with duplicate username fails"""
        user_data = {
            "username": "test_borrower",  # Already exists
            "email": "different@test.com",
            "password": "securepass123",
        }

        response = api_client.post("/api/lending/user/", user_data)

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print(f"Response data: {response.data}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data or "error" in response.data


@pytest.mark.django_db
class TestLoanApplication:
    """Test loan application process"""

    def test_create_loan_request_success(self, api_client, borrower_user):
        """Test successful loan application"""
        loan_data = {
            "borrower_id": borrower_user.id,
            "loan_amount": "5000.00",
            "loan_period_months": 12,
        }

        response = api_client.post("/api/lending/loan/", loan_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data["loan_amount"]) == Decimal("5000.00")
        assert response.data["loan_period_months"] == 12
        assert response.data["status"] == "pending"
        assert response.data["lender"] is None

        # Verify loan was created in database
        loan = Loan.objects.get(id=response.data["id"])
        assert loan.borrower == borrower_user
        assert loan.status == "pending"

    def test_create_loan_missing_fields(self, api_client, borrower_user):
        """Test loan creation with missing required fields"""
        loan_data = {
            "borrower_id": borrower_user.id,
            "loan_amount": "5000.00",
            # Missing loan_period_months
        }

        response = api_client.post("/api/lending/loan/", loan_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "are required" in response.data["error"]

    def test_create_loan_nonexistent_borrower(self, api_client):
        """Test loan creation with non-existent borrower"""
        loan_data = {
            "borrower_id": 999,  # Non-existent user
            "loan_amount": "5000.00",
            "loan_period_months": 12,
        }

        response = api_client.post("/api/lending/loan/", loan_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Borrower not found" in response.data["error"]

    def test_get_available_loans(self, api_client, sample_loan):
        """Test retrieving available loans"""
        response = api_client.get("/api/lending/loan-list/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == sample_loan.id
        assert response.data[0]["status"] == "pending"


@pytest.mark.django_db
class TestLoanOfferSystem:
    """Test loan offer submission and management"""

    def test_submit_offer_success(self, api_client, sample_loan, lender_user):
        """Test successful offer submission"""
        offer_data = {
            "loan_id": sample_loan.id,
            "lender_id": lender_user.id,
            "annual_interest_rate": "15.50",
        }

        response = api_client.post("/api/lending/offers/submit/", offer_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data["annual_interest_rate"]) == Decimal("15.50")
        assert response.data["loan"] == sample_loan.id
        assert response.data["lender"] == lender_user.id

        # Verify offer was created
        offer = LoanOffer.objects.get(id=response.data["id"])
        assert offer.loan == sample_loan
        assert offer.lender == lender_user
        assert not offer.is_accepted

    def test_submit_offer_insufficient_balance(
        self, api_client, sample_loan, poor_lender_user
    ):
        """Test offer submission with insufficient lender balance"""
        offer_data = {
            "loan_id": sample_loan.id,
            "lender_id": poor_lender_user.id,
            "annual_interest_rate": "15.50",
        }

        response = api_client.post("/api/lending/offers/submit/", offer_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient balance" in response.data["error"]
        assert "Required: $5003.75" in response.data["error"]  # loan_amount + lenme_fee

    def test_submit_offer_missing_fields(self, api_client, sample_loan, lender_user):
        """Test offer submission with missing fields"""
        offer_data = {
            "loan_id": sample_loan.id,
            "lender_id": lender_user.id,
            # Missing annual_interest_rate
        }

        response = api_client.post("/api/lending/offers/submit/", offer_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "are required" in response.data["error"]

    def test_submit_offer_nonexistent_loan(self, api_client, lender_user):
        """Test offer submission for non-existent loan"""
        offer_data = {
            "loan_id": 999,  # Non-existent loan
            "lender_id": lender_user.id,
            "annual_interest_rate": "15.50",
        }

        response = api_client.post("/api/lending/offers/submit/", offer_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Loan or Lender not found" in response.data["error"]


@pytest.mark.django_db
class TestOfferAcceptanceAndFunding:
    """Test offer acceptance and loan funding process"""

    def test_accept_offer_success(self, api_client, sample_offer, lender_user):
        """Test successful offer acceptance and loan funding"""
        assert sample_offer.loan.status == "pending"
        assert sample_offer.loan.lender is None
        assert not sample_offer.is_accepted

        initial_balance = lender_user.profile.balance

        accept_data = {"offer_id": sample_offer.id}

        response = api_client.post("/api/lending/offers/accept/", accept_data)

        assert response.status_code == status.HTTP_200_OK

        # Verify loan was updated
        loan_data = response.data
        assert loan_data["status"] == "funded"
        assert loan_data["lender"] == lender_user.id
        assert (
            Decimal(loan_data["annual_interest_rate"])
            == sample_offer.annual_interest_rate
        )
        assert Decimal(loan_data["lenme_fee"]) == Decimal("3.75")
        assert Decimal(loan_data["total_loan_amount"]) == Decimal("5003.75")

        # Verify database state
        sample_offer.refresh_from_db()
        assert sample_offer.is_accepted

        loan = sample_offer.loan
        loan.refresh_from_db()
        assert loan.status == "funded"
        assert loan.lender == lender_user
        assert loan.funded_at is not None

        # Verify lender balance was deducted
        lender_user.profile.refresh_from_db()
        expected_balance = initial_balance - Decimal("5003.75")
        assert lender_user.profile.balance == expected_balance

        # Verify payment schedule was created
        payments = Payment.objects.filter(loan=loan)
        assert len(payments) == 12  # 12 monthly payments

        # Verify payment calculation
        first_payment = payments.first()
        principal_portion = Decimal("5003.75") / 12  # ~417.00
        interest_portion = Decimal("5003.75") * (Decimal("15.50") / 100 / 12)  # ~64.55
        expected_payment = principal_portion + interest_portion
        assert abs(first_payment.amount - expected_payment) < Decimal("0.01")

    def test_accept_offer_insufficient_balance_at_acceptance(
        self, api_client, sample_offer, lender_user
    ):
        """Test offer acceptance when lender balance decreased after offer submission"""
        lender_user.profile.balance = Decimal("100.00")
        lender_user.profile.save()

        accept_data = {"offer_id": sample_offer.id}

        response = api_client.post("/api/lending/offers/accept/", accept_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Lender no longer has sufficient balance" in response.data["error"]

    def test_accept_offer_already_accepted(self, api_client, sample_offer):
        """Test accepting an already accepted offer"""
        sample_offer.is_accepted = True
        sample_offer.save()

        accept_data = {"offer_id": sample_offer.id}

        response = api_client.post("/api/lending/offers/accept/", accept_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Offer already accepted" in response.data["error"]

    def test_accept_nonexistent_offer(self, api_client):
        """Test accepting non-existent offer"""
        accept_data = {"offer_id": 999}  # Non-existent offer

        response = api_client.post("/api/lending/offers/accept/", accept_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Offer not found" in response.data["error"]

    def test_accept_offer_missing_offer_id(self, api_client):
        """Test accepting offer without providing offer_id"""
        accept_data = {}

        response = api_client.post("/api/lending/offers/accept/", accept_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "offer_id is required" in response.data["error"]


@pytest.mark.django_db
class TestPaymentScheduleCreation:
    """Test payment schedule creation and calculations"""

    def test_payment_schedule_creation(self, api_client, sample_offer):
        """Test that payment schedule is created correctly upon loan funding"""
        accept_data = {"offer_id": sample_offer.id}

        response = api_client.post("/api/lending/offers/accept/", accept_data)
        assert response.status_code == status.HTTP_200_OK

        loan = sample_offer.loan
        loan.refresh_from_db()

        payments = Payment.objects.filter(loan=loan).order_by("payment_number")

        # Verify correct number of payments
        assert len(payments) == loan.loan_period_months

        # Verify payment numbering
        for i, payment in enumerate(payments, 1):
            assert payment.payment_number == i
            assert payment.status == "pending"
            assert payment.due_date is not None

        # Verify payment calculation (simple interest)
        principal_portion = loan.total_loan_amount / loan.loan_period_months
        interest_portion = loan.total_loan_amount * (
            loan.annual_interest_rate / 100 / 12
        )
        expected_payment = principal_portion + interest_portion

        for payment in payments:
            assert abs(payment.amount - expected_payment) < Decimal("0.01")

    def test_zero_interest_payment_calculation(
        self, api_client, sample_loan, lender_user
    ):
        """Test payment calculation with zero interest rate"""
        # Create offer with 0% interest
        zero_interest_offer = LoanOffer.objects.create(
            loan=sample_loan, lender=lender_user, annual_interest_rate=Decimal("0.00")
        )

        accept_data = {"offer_id": zero_interest_offer.id}

        response = api_client.post("/api/lending/offers/accept/", accept_data)
        assert response.status_code == status.HTTP_200_OK

        loan = zero_interest_offer.loan
        loan.refresh_from_db()

        payments = Payment.objects.filter(loan=loan)

        # With 0% interest, payment should be just principal divided by months
        expected_payment = loan.total_loan_amount / loan.loan_period_months

        for payment in payments:
            # Round both values to 2 decimal places for comparison (database precision)
            assert payment.amount == expected_payment.quantize(Decimal("0.01"))


@pytest.mark.django_db
class TestLoanDetails:
    """Test loan detail retrieval"""

    def test_get_loan_details(self, api_client, funded_loan):
        """Test retrieving loan details with payment schedule"""
        Payment.objects.create(
            loan=funded_loan,
            payment_number=1,
            amount=Decimal("500.00"),
            due_date=timezone.now().date(),
        )

        response = api_client.get(f"/api/lending/loan/{funded_loan.id}/")

        assert response.status_code == status.HTTP_200_OK

        loan_data = response.data["loan"]
        payments_data = response.data["payments"]

        assert loan_data["id"] == funded_loan.id
        assert loan_data["status"] == "funded"
        assert len(payments_data) == 1
        assert Decimal(payments_data[0]["amount"]) == Decimal("500.00")

    def test_get_nonexistent_loan_details(self, api_client):
        """Test retrieving details for non-existent loan"""
        response = api_client.get("/api/lending/loan/999/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Loan not found" in response.data["error"]


@pytest.mark.django_db
class TestIntegrationWorkflow:
    """Integration tests for complete lending workflow"""

    def test_complete_lending_workflow(self, api_client):
        """Test the complete workflow from user creation to loan funding"""

        borrower_data = {
            "username": "workflow_borrower",
            "email": "borrower@workflow.com",
            "password": "securepass123",
            "user_type": "borrower",
        }

        borrower_response = api_client.post("/api/lending/user/", borrower_data)
        assert borrower_response.status_code == status.HTTP_201_CREATED
        borrower_id = borrower_response.data["id"]

        # Step 2: Create lender with sufficient balance
        lender_data = {
            "username": "workflow_lender",
            "email": "lender@workflow.com",
            "password": "securepass123",
            "user_type": "lender",
        }

        lender_response = api_client.post("/api/lending/user/", lender_data)
        assert lender_response.status_code == status.HTTP_201_CREATED
        lender_id = lender_response.data["id"]

        # Manually set lender balance (in real app, this would be done through deposit)
        lender_user = User.objects.get(id=lender_id)
        lender_user.profile.balance = Decimal("10000.00")
        lender_user.profile.user_type = "lender"
        lender_user.profile.save()

        # Step 3: Borrower creates loan request
        loan_data = {
            "borrower_id": borrower_id,
            "loan_amount": "3000.00",
            "loan_period_months": 6,
        }

        loan_response = api_client.post("/api/lending/loan/", loan_data)
        assert loan_response.status_code == status.HTTP_201_CREATED
        loan_id = loan_response.data["id"]

        # Step 4: Lender submits offer
        offer_data = {
            "loan_id": loan_id,
            "lender_id": lender_id,
            "annual_interest_rate": "18.00",
        }

        offer_response = api_client.post("/api/lending/offers/submit/", offer_data)
        assert offer_response.status_code == status.HTTP_201_CREATED
        offer_id = offer_response.data["id"]

        # Step 5: Borrower accepts offer
        accept_data = {"offer_id": offer_id}

        accept_response = api_client.post("/api/lending/offers/accept/", accept_data)
        assert accept_response.status_code == status.HTTP_200_OK

        # Verify final state
        final_loan_data = accept_response.data
        assert final_loan_data["status"] == "funded"
        assert Decimal(final_loan_data["loan_amount"]) == Decimal("3000.00")
        assert Decimal(final_loan_data["annual_interest_rate"]) == Decimal("18.00")
        assert Decimal(final_loan_data["total_loan_amount"]) == Decimal("3003.75")

        # Verify payment schedule was created
        loan = Loan.objects.get(id=loan_id)
        payments = Payment.objects.filter(loan=loan)
        assert len(payments) == 6

        # Verify lender balance was deducted
        lender_user.profile.refresh_from_db()
        assert lender_user.profile.balance == Decimal("6996.25")  # 10000 - 3003.75
