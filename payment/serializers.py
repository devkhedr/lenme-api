from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "loan",
            "payment_number",
            "amount",
            "due_date",
            "status",
            "paid_at",
            "platform_fee",
            "lender_amount",
        ]
        read_only_fields = ["id", "paid_at", "platform_fee", "lender_amount"]
