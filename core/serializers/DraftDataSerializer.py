# core/serializers/draft_serializers.py

from rest_framework import serializers
from core.services.receipt_validation import ReceiptValidationService
from core.serializers.ReceiptSerializer import ContactValidatorSerializer, WithholdingSerializer


class DraftDataSerializer(serializers.Serializer):
    """
    Lightweight serializer for draft autosave.
    Delegates all validation to ReceiptValidationService.
    Preserves ALL fields exactly as sent.
    """

    # ========================
    # Allow all fields — no strict typing
    # ========================
    receipt_number = serializers.CharField()
    receipt_date = serializers.DateField()
    calendar_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    machine_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Classification IDs — serializers.IntegerField() removed
    receipt_category_id = serializers.IntegerField(required=False)
    receipt_kind_id = serializers.IntegerField(required=False)
    receipt_type_id = serializers.IntegerField(required=False)
    receipt_name_id = serializers.IntegerField(required=False)

    is_withholding_applicable = serializers.BooleanField(required=False)
    payment_method_type = serializers.CharField()
    bank_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reason_of_receiving = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Nested
    issued_by_details = ContactValidatorSerializer()
    issued_to_details = ContactValidatorSerializer()
    withholding_details = WithholdingSerializer(required=False, allow_null=True)

    # Items
    items = serializers.ListField(child=serializers.DictField())

    # Files (ignored)
    main_receipt_document = serializers.FileField(required=False, read_only=True)
    attachement_receipt = serializers.FileField(required=False, read_only=True)

    def validate(self, attrs):
        """
        Delegate all validation to ReceiptValidationService
        """
        try:
            validated_data = ReceiptValidationService.validate_receipt_data(attrs, recorded_by=None)
            return validated_data  # ✅ This now includes receipt_category_id, etc.
        except Exception as e:
            if isinstance(e, serializers.ValidationError):
                raise e
            else:
                raise serializers.ValidationError({"non_field_errors": str(e)})