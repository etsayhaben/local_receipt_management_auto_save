# core/serializers/lookups.py

from rest_framework import serializers
from core.models.look_up_tables import (
    ReceiptName,
    ReceiptKind,
    ReceiptCatagory,
    ReceiptType,
)


class ReceiptNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptName
        fields = ["id", "name"]


class ReceiptKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptKind
        fields = ["id", "name"]

# core/serializers/ContactSerializer.py
from rest_framework import serializers
from core.models.contact import Contact



class ReceiptCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptCatagory
        fields = ["id", "name"]


class ReceiptTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptType
        fields = ["id", "name"]
