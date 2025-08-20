# core/serializers/ReceiptDisplaySerializer.py
from rest_framework import serializers
from decimal import Decimal
from core.models.Documents import ReceiptDocument
from core.models.Receipt import Receipt, ThirtyPercentWithholdingReceipt
from core.models.contact import Contact
from core.models.item import Item
from core.models.CRVITEM import CRVItem
from core.models.Receipt import ReceiptLine
from core.services.RetrivingFromLookUpTables import RetrievingFromLookupTables


# ✅ Use unique ref_name to avoid drf_yasg conflict
class ContactDisplaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["name", "tin_number", "address"]
        ref_name = "ReceiptDisplayContact"  # ← Prevents Swagger conflict


class ItemDisplaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            "item_code",
            "item_description",
            "unit_of_measurement",
            "gl_account",
            "nature",
            "tax_type",
            "unit_cost",
        ]
        ref_name = "ReceiptDisplayItem"


class ReceiptLineDisplaySerializer(serializers.ModelSerializer):
    item = ItemDisplaySerializer(read_only=True)

    class Meta:
        model = ReceiptLine
        fields = [
            "id",
            "item",
            "quantity",
            "unit_cost",
            "tax_type",
            "tax_amount",
            "discount_amount",
            "subtotal",
            "total_after_tax",
        ]


class CRVItemDisplaySerializer(serializers.ModelSerializer):
    class Meta:
        model = CRVItem
        fields = [
            "id",
            "gl_account",
            "nature",
            "quantity",
            "amount_per_unit",
            "total_amount",
            "reason_of_receiving",
            "transaction_description",
        ]


from django.utils.html import strip_tags
from rest_framework import serializers
from decimal import Decimal

class ReceiptDisplaySerializer(serializers.ModelSerializer):
    # Issuer and receiver details
    issued_by_details = ContactDisplaySerializer(source="issued_by", read_only=True)
    issued_to_details = ContactDisplaySerializer(source="issued_to", read_only=True)

    # Line items (dynamic based on category)
    items = serializers.SerializerMethodField()

    # Financial fields
    subtotal = serializers.SerializerMethodField()
    tax = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    withholding_amount = serializers.SerializerMethodField()
    net_payable_to_supplier = serializers.SerializerMethodField()

    # Lookup table fields
    receipt_category = serializers.SerializerMethodField()
    receipt_kind = serializers.SerializerMethodField()
    receipt_type = serializers.SerializerMethodField()
    receipt_name = serializers.SerializerMethodField()

    # Linked documents (main + withholding receipts)
    documents = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = [
            "id",
            "receipt_number",
            "machine_number",
            "receipt_date",
            "calendar_type",
            "issued_by_details",
            "issued_to_details",
            "receipt_category",
            "receipt_kind",
            "receipt_type",
            "receipt_name",
            "is_withholding_applicable",
            "payment_method_type",
            "bank_name",
            "items",
            "withholding_receipt_number",
            "reason_of_receiving",
            "created_at",
            "updated_at",
            "subtotal",
            "tax",
            "total",
            "withholding_amount",
            "net_payable_to_supplier",
            "documents",
        ]
        read_only_fields = fields  # All fields are read-only

    # --- Field Methods ---

    def get_receipt_category(self, obj):
        name = RetrievingFromLookupTables.get_category_name_by_id(obj.receipt_category_id)
        return strip_tags(name.strip()) if name else None

    def get_receipt_kind(self, obj):
        name = RetrievingFromLookupTables.get_kind_name_by_id(obj.receipt_kind_id)
        return strip_tags(name.strip()) if name else None

    def get_receipt_type(self, obj):
        name = RetrievingFromLookupTables.get_type_name_by_id(obj.receipt_type_id)
        return strip_tags(name.strip()) if name else None

    def get_receipt_name(self, obj):
        name = RetrievingFromLookupTables.get_name_name_by_id(obj.receipt_name_id)
        return strip_tags(name.strip()) if name else None

    def get_items(self, obj):
        category_name = self.get_receipt_category(obj)
        if category_name and category_name.lower() == "crv":
            return CRVItemDisplaySerializer(obj.crvitem_set.all(), many=True).data
        else:
            return ReceiptLineDisplaySerializer(obj.items.all(), many=True).data

    def get_subtotal(self, obj):
        return str(obj.subtotal.quantize(Decimal("0.00")))

    def get_tax(self, obj):
        return str(obj.tax.quantize(Decimal("0.00")))

    def get_total(self, obj):
        return str(obj.total.quantize(Decimal("0.00")))

    def get_withholding_amount(self, obj):
        if obj.is_withholding_applicable:
            amount = (obj.subtotal * Decimal("0.02")).quantize(Decimal("0.00"))
            return str(amount)
        return "0.00"

    def get_net_payable_to_supplier(self, obj):
        withholding = Decimal(self.get_withholding_amount(obj))
        net = (obj.total - withholding).quantize(Decimal("0.00"))
        return str(net)

    def get_documents(self, obj):
        """
        Returns metadata about uploaded main and withholding receipt documents
        linked to this Receipt via ReceiptDocument.source_document
        """
        try:
            # Get the ReceiptDocument linked to this Receipt
            receipt_document = getattr(obj, 'source_document', None)
            if not receipt_document:
                return {}

            data = {}

            # --- Main Receipt Document ---
            main_doc = receipt_document.main_receipt  # This is a MainReceiptDocument
            if main_doc and main_doc.main_receipt:
                try:
                    file_url = main_doc.main_receipt.url
                except ValueError:
                    file_url = None

                data["main_receipt"] = {
                    "file": file_url,
                    "filename": main_doc.main_receipt_filename or f"{main_doc.receipt_number}.pdf",
                    "content_type": main_doc.main_receipt_content_type or "application/pdf",
                    "uploaded_at": main_doc.uploaded_at,
                    "receipt_number": main_doc.receipt_number,
                }

            # --- Withholding Receipt Document ---
            withholding_doc = receipt_document.withholding_receipt  # This is a WithholdingReceiptDocument
            if withholding_doc and withholding_doc.withholding_receipt:
                try:
                    file_url = withholding_doc.withholding_receipt.url
                except ValueError:
                    file_url = None

                data["withholding_receipt"] = {
                    "file": file_url,
                    "filename": withholding_doc.withholding_receipt_filename or f"{withholding_doc.withholding_receipt_number}.pdf",
                    "content_type": withholding_doc.withholding_receipt_content_type or "application/pdf",
                    "uploaded_at": withholding_doc.uploaded_at,
                    "receipt_number": withholding_doc.withholding_receipt_number,
                }

            return data

        except Exception as e:
            # Use proper logging in production
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Failed to load documents for receipt {obj.receipt_number}")

            return {"error": "Failed to load document metadata"}


class ThirtyPercentWithholdingReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThirtyPercentWithholdingReceipt
        fields = [
            "id",
            "supplier_name",
            "withholding_receipt_number",
            "withholding_receipt_date",
            "transaction_description",
            "sub_total",
            "tax_withholding_amount",  # Read-only via calculation
            "buyer_tin",
            "seller_tin",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["tax_withholding_amount", "created_at", "updated_at"]

    def validate_withholding_receipt_number(self, value):
        """Ensure unique receipt number (case-insensitive)."""
        qs = ThirtyPercentWithholdingReceipt.objects.filter(
            withholding_receipt_number__iexact=value
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A receipt with this number already exists."
            )
        return value

    def create(self, validated_data):
        # Remove any client-provided tax_withholding_amount
        validated_data.pop("tax_withholding_amount", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Ensure tax_withholding_amount is never updated manually
        validated_data.pop("tax_withholding_amount", None)
        return super().update(instance, validated_data)
