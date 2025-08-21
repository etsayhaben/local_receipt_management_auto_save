# core/serializers/draft_serializers.py
# core/serializers/draft_serializers.py
# Services
# Services
from rest_framework import serializers
from core.services.receipt_validation import ReceiptValidationService
from rest_framework import serializers
from core.services.receipt_validation import ReceiptValidationService
from core.serializers.ReceiptSerializer import ContactValidatorSerializer, WithholdingSerializer


class DraftDataSerializer(serializers.Serializer):
    """
    Accepts the SAME JSON structure as ReceiptSerializer.
    No draft_id, no data wrapper — just full receipt-like input.
    """

    # ========================
    # NESTED SERIALIZERS
    # ========================
    issued_by_details = ContactValidatorSerializer()
    issued_to_details = ContactValidatorSerializer()
    withholding_details = WithholdingSerializer(required=False, allow_null=True)
    machine_number = serializers.CharField(allow_blank=True, required=False)

    # ========================
    # CORE FIELDS
    # ========================
    receipt_number = serializers.CharField(
        max_length=50,
        required=True,
        allow_blank=False
    )
    receipt_date = serializers.DateField()
    calendar_type = serializers.ChoiceField(
        choices=["gregorian", "ethiopian"],
        required=False,
        allow_null=True
    )

    # Classification IDs
    receipt_category_id = serializers.IntegerField()
    receipt_kind_id = serializers.IntegerField()
    receipt_type_id = serializers.IntegerField()
    receipt_name_id = serializers.IntegerField()

    is_withholding_applicable = serializers.BooleanField(default=False)
    payment_method_type = serializers.CharField(max_length=50)
    bank_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    # Line Items
    items = serializers.ListField(child=serializers.DictField())

    # Files (ignored in draft — passed to service later)
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
    # VALIDATION (same as final, but no business rules)
    # ========================
    def validate(self, attrs):
        # ✅ Use shared validation logic
        try:
            # Pass attrs directly — ReceiptValidationService handles structure
            validated_data = ReceiptValidationService.validate_receipt_data(attrs, recorded_by=None)
        except Exception as e:
            if isinstance(e, serializers.ValidationError):
                raise e
            else:
                raise serializers.ValidationError({"non_field_errors": str(e)})

        return validated_data