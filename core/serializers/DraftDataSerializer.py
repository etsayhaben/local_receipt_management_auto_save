# core/serializers/draft_serializers.py

from rest_framework import serializers
from core.services.draft_validation import DraftValidationService

class DraftDataSerializer(serializers.Serializer):
    # No field definitions — pass everything to validate()

    def validate(self, attrs):
        try:
            return DraftValidationService.validate_draft_data(attrs)
        except Exception as e:
            if isinstance(e, serializers.ValidationError):
                raise e
            else:
                # Log but don't block
                print("Draft validation warning:", str(e))
                return attrs  # Save partial data