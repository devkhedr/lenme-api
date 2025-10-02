from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "loan",
        "payment_number",
        "amount",
        "due_date",
        "status",
        "paid_at",
    ]
    list_filter = ["status"]
    ordering = ["loan", "payment_number"]
