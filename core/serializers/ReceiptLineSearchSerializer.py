# serializers/ReceiptLineSearchSerializer.py
from rest_framework import serializers
from core.models.Receipt import ReceiptLine


class ReceiptLineSearchSerializer(serializers.ModelSerializer):
    item_code = serializers.SerializerMethodField()
    item_description = serializers.SerializerMethodField()
    declaration_number = serializers.SerializerMethodField()
    receipt_number = serializers.SerializerMethodField()
    receipt_date = serializers.SerializerMethodField()
    issued_to = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    vat_amount = serializers.SerializerMethodField()
    total_after_tax = serializers.SerializerMethodField()
    is_vat_expired = serializers.SerializerMethodField()
    claimable_vat = serializers.SerializerMethodField()
    non_claimable_vat = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptLine
        fields = [
            "item_code",
            "item_description",
            "quantity",
            "unit_cost",
            "declaration_number",
            "subtotal",
            "vat_amount",
            "total_after_tax",
            "receipt_number",
            "receipt_date",
            "issued_to",
            "is_vat_expired",
            "claimable_vat",
            "non_claimable_vat",
        ]

    def get_item_code(self, obj):
        return obj.item.item_code if obj.item else None

    def get_item_description(self, obj):
        return obj.item.item_description if obj.item else None

    def get_declaration_number(self, obj):
        return (
            obj.item.declaration_number
            if obj.item and obj.item.declaration_number
            else None
        )

    def get_receipt_number(self, obj):
        return obj.receipt.receipt_number if obj.receipt else None

    def get_receipt_date(self, obj):
        return obj.receipt.receipt_date if obj.receipt else None

    def get_issued_to(self, obj):
        return (
            obj.receipt.issued_to.name
            if obj.receipt and obj.receipt.issued_to
            else None
        )

    def get_subtotal(self, obj):
        return obj.subtotal

    def get_vat_amount(self, obj):
        return obj.tax_amount

    def get_total_after_tax(self, obj):
        return obj.total_after_tax

    def get_is_vat_expired(self, obj):
        return obj.receipt.is_vat_expired if obj.receipt else False

    def get_claimable_vat(self, obj):
        return obj.receipt.claimable_vat if obj.receipt else 0

    def get_non_claimable_vat(self, obj):
        return obj.receipt.non_claimable_vat if obj.receipt else 0
