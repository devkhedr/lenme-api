from rest_framework import serializers
from .models import Loan, LoanOffer, UserProfile
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    user_type = serializers.ChoiceField(
        choices=[("borrower", "Borrower"), ("lender", "Lender")]
    )
    balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0, required=False
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "user_type", "balance"]
        extra_kwargs = {
            "email": {"required": True},
        }

    def create(self, validated_data):
        user_type = validated_data.pop("user_type")
        balance = validated_data.pop("balance", 0)

        # Create the user
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )

        # Create the user profile
        UserProfile.objects.create(user=user, user_type=user_type, balance=balance)

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = UserProfile
        fields = ["user", "balance", "user_type"]


class LoanSerializer(serializers.ModelSerializer):
    borrower_username = serializers.CharField(
        source="borrower.username", read_only=True
    )
    lender_username = serializers.CharField(
        source="lender.username", read_only=True, allow_null=True
    )

    class Meta:
        model = Loan
        fields = [
            "id",
            "borrower",
            "borrower_username",
            "lender",
            "lender_username",
            "loan_amount",
            "loan_period_months",
            "annual_interest_rate",
            "lenme_fee",
            "total_loan_amount",
            "status",
            "created_at",
            "funded_at",
        ]
        read_only_fields = [
            "id",
            "lender",
            "annual_interest_rate",
            "lenme_fee",
            "total_loan_amount",
            "status",
            "created_at",
            "funded_at",
        ]


class LoanOfferSerializer(serializers.ModelSerializer):
    lender_username = serializers.CharField(source="lender.username", read_only=True)

    class Meta:
        model = LoanOffer
        fields = [
            "id",
            "loan",
            "lender",
            "lender_username",
            "annual_interest_rate",
            "created_at",
            "is_accepted",
        ]
        read_only_fields = ["id", "created_at", "is_accepted"]
