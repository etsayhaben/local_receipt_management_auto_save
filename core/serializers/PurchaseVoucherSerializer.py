# core/serializers/PurchaseVoucherSerializer.py
from rest_framework import serializers
from core.models.PurchaseVoucher import PurchaseVoucher


class PurchaseVoucherSerializer(serializers.ModelSerializer):
    document = serializers.FileField(required=False, write_only=True)
    attachment = serializers.FileField(required=False, write_only=True)

    class Meta:
        model = PurchaseVoucher
        fields = "__all__"

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.FILES:
            doc_file = request.FILES.get("document")
            attach_file = request.FILES.get("attachment")

            if doc_file:
                validated_data["document"] = doc_file.read()
                validated_data["document_filename"] = doc_file.name
                validated_data["document_content_type"] = doc_file.content_type

            if attach_file:
                validated_data["attachment"] = attach_file.read()
                validated_data["attachment_filename"] = attach_file.name
                validated_data["attachment_content_type"] = attach_file.content_type

        return super().create(validated_data)
