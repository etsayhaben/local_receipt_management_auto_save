# core/services/receipt_validation.py

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models.look_up_tables import (
    ReceiptCatagory,
    ReceiptKind,
    ReceiptType,
    ReceiptName,
)
from core.models.contact import Contact
from core.models.item import Item
# from core.serializers.ReceiptSerializer import CRVItemSerializer, ReceiptLineSerializer  # Removed to avoid circular import
# Import your item serializers


class ReceiptValidationService:
    @staticmethod
    def validate_receipt_data(data: dict, recorded_by: Contact = None) -> dict:
        """
        Validates receipt data structure.
        Used by both DraftSerializer and ReceiptSerializer.
        Does NOT create objects or enforce final business rules.
        """
        validated = {}

        # ========================
        # 1. Core Fields
        # ========================
        receipt_number = data.get("receipt_number", "").strip()
        if not receipt_number:
            raise ValidationError({"receipt_number": "This field is required."})
        validated["receipt_number"] = receipt_number

        receipt_date = data.get("receipt_date")
        if not receipt_date:
            raise ValidationError({"receipt_date": "This field is required."})
        validated["receipt_date"] = receipt_date

        calendar_type = data.get("calendar_type")
        if calendar_type not in [None, "", "gregorian", "ethiopian"]:
            raise ValidationError({"calendar_type": "Invalid calendar type."})
        validated["calendar_type"] = calendar_type

        payment_method_type = data.get("payment_method_type")
        if not payment_method_type:
            raise ValidationError({"payment_method_type": "This field is required."})
        validated["payment_method_type"] = payment_method_type

        validated["bank_name"] = data.get("bank_name", "")
        validated["machine_number"] = data.get("machine_number", "")
        validated["reason_of_receiving"] = data.get("reason_of_receiving")
        validated["is_withholding_applicable"] = data.get("is_withholding_applicable", False)

        # ========================
        # 2. Contacts
        # ========================
        issued_by_data = data.get("issued_by_details")
        issued_to_data = data.get("issued_to_details")

        if not issued_by_data:
            raise ValidationError({"issued_by_details": ["This field is required."]})
        if not issued_to_data:
            raise ValidationError({"issued_to_details": ["This field is required."]})

        validated["issued_by_details"] = issued_by_data
        validated["issued_to_details"] = issued_to_data

        # ========================
        # 3. Classification IDs
        # ========================
        category_id = data.get("receipt_category_id")
        kind_id = data.get("receipt_kind_id")
        type_id = data.get("receipt_type_id")
        name_id = data.get("receipt_name_id")

        try:
            receipt_category = ReceiptCatagory.objects.get(id=category_id)
            validated["receipt_category"] = receipt_category
        except ReceiptCatagory.DoesNotExist:
            raise ValidationError({"receipt_category_id": "Invalid category ID."})

        try:
            receipt_kind = ReceiptKind.objects.get(id=kind_id)
            validated["receipt_kind"] = receipt_kind
        except ReceiptKind.DoesNotExist:
            raise ValidationError({"receipt_kind_id": "Invalid kind ID."})

        try:
            receipt_type = ReceiptType.objects.get(id=type_id)
            validated["receipt_type"] = receipt_type
        except ReceiptType.DoesNotExist:
            raise ValidationError({"receipt_type_id": "Invalid type ID."})

        try:
            receipt_name = ReceiptName.objects.get(id=name_id)
            validated["receipt_name"] = receipt_name
        except ReceiptName.DoesNotExist:
            raise ValidationError({"receipt_name_id": "Invalid name ID."})

        # ========================
        # 4. Items
        # ========================
        items_data = data.get("items", [])
        if not items_data:
            raise ValidationError({"items": ["At least one item is required."]})

        # Basic item validation without serializers to avoid circular imports
        validated_items = []
        for idx, item_data in enumerate(items_data):
            # Basic validation for required fields
            if not item_data.get("item_description"):
                raise ValidationError({"items": [f"Item {idx + 1}: item_description is required"]})
            
            # Validate numeric fields
            try:
                quantity = float(item_data.get("quantity", 1))
                if quantity <= 0:
                    raise ValidationError({"items": [f"Item {idx + 1}: quantity must be greater than 0"]})
            except (ValueError, TypeError):
                raise ValidationError({"items": [f"Item {idx + 1}: invalid quantity value"]})
            
            try:
                unit_cost = float(item_data.get("unit_cost", 0))
                if unit_cost < 0:
                    raise ValidationError({"items": [f"Item {idx + 1}: unit_cost cannot be negative"]})
            except (ValueError, TypeError):
                raise ValidationError({"items": [f"Item {idx + 1}: invalid unit_cost value"]})
            
            validated_items.append(item_data)

        validated["items"] = validated_items

        return validated