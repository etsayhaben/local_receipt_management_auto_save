# core/services/draft_validation.py

from rest_framework import serializers

class DraftValidationService:
    """
    Lightweight validation for draft autosave.
    Allows partial data.
    Only validates structure, not required fields.
    """

    @staticmethod
    def validate_draft_data(data: dict) -> dict:
        validated = {}

        # Optional: receipt_number
        if "receipt_number" in data and data["receipt_number"]:
            validated["receipt_number"] = data["receipt_number"].strip()

        # Optional: receipt_date
        if "receipt_date" in data:
            validated["receipt_date"] = data["receipt_date"]

        # Optional: calendar_type
        if "calendar_type" in data:
            if data["calendar_type"] in ["gregorian", "ethiopian", None, ""]:
                validated["calendar_type"] = data["calendar_type"]
            else:
                raise serializers.ValidationError({"calendar_type": "Invalid value"})

        # Optional: payment
        if "payment_method_type" in data:
            validated["payment_method_type"] = data["payment_method_type"]
        if "bank_name" in data:
            validated["bank_name"] = data["bank_name"]
        if "machine_number" in data:
            validated["machine_number"] = data["machine_number"]

        # Optional: contacts
        if "issued_by_details" in data and data["issued_by_details"]:
            # Basic structure
            issued_by = data["issued_by_details"]
            validated["issued_by_details"] = {
                "name": issued_by.get("name", ""),
                "tin_number": issued_by.get("tin_number", ""),
                "address": issued_by.get("address", "")
            }

        if "issued_to_details" in data and data["issued_to_details"]:
            issued_to = data["issued_to_details"]
            validated["issued_to_details"] = {
                "name": issued_to.get("name", ""),
                "tin_number": issued_to.get("tin_number", ""),
                "address": issued_to.get("address", "")
            }

        # Optional: classification IDs
        for field in ["receipt_category_id", "receipt_kind_id", "receipt_type_id", "receipt_name_id"]:
            if field in data and data[field] is not None:
                try:
                    validated[field] = int(data[field])
                except (ValueError, TypeError):
                    raise serializers.ValidationError({field: "Must be integer"})

        # Optional: items
        if "items" in data:
            validated_items = []
            for idx, item in enumerate(data["items"]):
                cleaned = {
                    "item_code": item.get("item_code", ""),
                    "item_description": item.get("item_description", ""),
                    "quantity": item.get("quantity", "1.00"),
                    "unit_cost": item.get("unit_cost", "0.00"),
                    "tax_type": item.get("tax_type", ""),
                    "tax_amount": item.get("tax_amount", "0.00"),
                    "discount_amount": item.get("discount_amount", "0.00")
                }
                validated_items.append(cleaned)
            validated["items"] = validated_items

        # Pass through anything else
        for key, value in data.items():
            if key not in validated:
                validated[key] = value

        return validated