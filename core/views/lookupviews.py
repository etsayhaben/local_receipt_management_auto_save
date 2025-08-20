# core/views/lookups.py

from rest_framework import generics
from rest_framework.permissions import AllowAny
from core.models.look_up_tables import (
    ReceiptName,
    ReceiptKind,
    ReceiptCatagory,
    ReceiptType,
)
from core.serializers.look_up_table_serializer import (
    ReceiptNameSerializer,
    ReceiptKindSerializer,
    ReceiptCategorySerializer,
    ReceiptTypeSerializer,
)


# ----------- Receipt Kind ----------
class ReceiptKindListAPIView(generics.ListAPIView):
    queryset = ReceiptKind.objects.all()
    serializer_class = ReceiptKindSerializer
    permission_classes = [AllowAny]


class ReceiptKindCreateView(generics.CreateAPIView):
    queryset = ReceiptKind.objects.all()
    serializer_class = ReceiptKindSerializer
    permission_classes = [AllowAny]


# ----------- Receipt Name ----------
class ReceiptNameListAPIView(generics.ListAPIView):
    queryset = ReceiptName.objects.all()
    serializer_class = ReceiptNameSerializer
    permission_classes = [AllowAny]


class ReceiptNameCreateView(generics.CreateAPIView):
    queryset = ReceiptName.objects.all()
    serializer_class = ReceiptNameSerializer
    permission_classes = [AllowAny]


# ----------- Receipt Category ----------
class ReceiptCategoryListAPIView(generics.ListAPIView):
    queryset = ReceiptCatagory.objects.all()
    serializer_class = ReceiptCategorySerializer
    permission_classes = [AllowAny]


class ReceiptCategoryCreateView(generics.CreateAPIView):
    queryset = ReceiptCatagory.objects.all()
    serializer_class = ReceiptCategorySerializer
    permission_classes = [AllowAny]


# ----------- Receipt Type ----------
class ReceiptTypeListAPIView(generics.ListAPIView):
    queryset = ReceiptType.objects.all()
    serializer_class = ReceiptTypeSerializer
    permission_classes = [AllowAny]


class ReceiptTypeCreateView(generics.CreateAPIView):
    queryset = ReceiptType.objects.all()
    serializer_class = ReceiptTypeSerializer
    permission_classes = [AllowAny]
