import os
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from decimal import Decimal
from lending.models import Loan, LoanOffer, UserProfile
from payment.models import Payment


@pytest.fixture
def api_client():
    """Returns API client for making requests"""
    return APIClient()


def lending_url(path):
    """Helper to build lending API URLs"""
    return f"/api/lending/{path.lstrip('/')}"


def payment_url(path):
    """Helper to build payment API URLs"""
    return f"/api/payment/{path.lstrip('/')}"


@pytest.fixture
def borrower_user():
    """Creates a borrower user with profile"""
    user = User.objects.create_user(
        username="test_borrower", email="borrower@test.com", password="testpass123"
    )
    UserProfile.objects.create(user=user, user_type="borrower", balance=Decimal("0.00"))
    return user


@pytest.fixture
def lender_user():
    """Creates a lender user with sufficient balance"""
    user = User.objects.create_user(
        username="test_lender", email="lender@test.com", password="testpass123"
    )
    UserProfile.objects.create(
        user=user, user_type="lender", balance=Decimal("10000.00")
    )
    return user


@pytest.fixture
def poor_lender_user():
    """Creates a lender user with insufficient balance"""
    user = User.objects.create_user(
        username="poor_lender", email="poor_lender@test.com", password="testpass123"
    )
    UserProfile.objects.create(user=user, user_type="lender", balance=Decimal("100.00"))
    return user


@pytest.fixture
def sample_loan(borrower_user):
    """Creates a sample loan for testing"""
    return Loan.objects.create(
        borrower=borrower_user,
        loan_amount=Decimal("5000.00"),
        loan_period_months=12,
        status="pending",
    )


@pytest.fixture
def funded_loan(borrower_user, lender_user):
    """Creates a funded loan for payment testing"""
    return Loan.objects.create(
        borrower=borrower_user,
        lender=lender_user,
        loan_amount=Decimal("5000.00"),
        loan_period_months=12,
        annual_interest_rate=Decimal("12.00"),
        lenme_fee=Decimal("3.75"),
        total_loan_amount=Decimal("5003.75"),
        status="funded",
    )


@pytest.fixture
def sample_offer(sample_loan, lender_user):
    """Creates a sample loan offer"""
    return LoanOffer.objects.create(
        loan=sample_loan, lender=lender_user, annual_interest_rate=Decimal("15.50")
    )
