# core/serializers/draft_serializers.py

from rest_framework import serializers

# Services
from core.services.receipt_validation import ReceiptValidationService


class DraftDataSerializer(serializers.Serializer):
    """
    Lightweight serializer for draft autosave.
    Validates structure like ReceiptSerializer, but without final rules.
    Does NOT create objects or enforce business constraints.
    """

    # ========================
    # CORE FIELDS (all optional for draft)
    # ========================
    receipt_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=False,
        help_text="e.g., FS246, M751"
    )
    receipt_date = serializers.DateField(required=False)
    calendar_type = serializers.ChoiceField(
        choices=["gregorian", "ethiopian"],
        required=False,
        allow_null=True
    )

    # Classification IDs
    receipt_category_id = serializers.IntegerField(required=False)
    receipt_kind_id = serializers.IntegerField(required=False)
    receipt_type_id = serializers.IntegerField(required=False)
    receipt_name_id = serializers.IntegerField(required=False)

    # Parties
    issued_by_details = serializers.DictField(required=False)
    issued_to_details = serializers.DictField(required=False)

    # Payment
    is_withholding_applicable = serializers.BooleanField(required=False)
    payment_method_type = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True
    )
    bank_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True
    )
    machine_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    # Line Items
    items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of item dictionaries"
    )

    # Misc
    reason_of_receiving = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )

    # Files (ignore in draft — not saved here)
    main_receipt_document = serializers.FileField(
        required=False,
        allow_null=True,
        read_only=True  # Don't accept files in draft
    )
    attachement_receipt = serializers.FileField(
        required=False,
        allow_null=True,
        read_only=True
    )

    # ========================
    # VALIDATION
    # ========================
    def validate(self, attrs):
        # ✅ Use shared validation logic
        try:
            # Pass attrs directly — ReceiptValidationService handles structure
            validated_data = ReceiptValidationService.validate_receipt_data(attrs, recorded_by=None)
        except Exception as e:
            # Convert any ValidationError to DRF format
            if isinstance(e, serializers.ValidationError):
                raise e
            elif isinstance(e, Exception):
                # Wrap in ValidationError
                raise serializers.ValidationError({"non_field_errors": str(e)})
            else:
                raise serializers.ValidationError({"non_field_errors": "Validation failed."})

        return validated_data