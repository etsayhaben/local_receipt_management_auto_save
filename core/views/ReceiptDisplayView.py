# core/views/ReceiptDisplayView.py
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.models.Receipt import Receipt, ThirtyPercentWithholdingReceipt
from core.models.Documents import ReceiptDocument  # ← Add this
from core.serializers.ReceiptDisplaySerializer import (
    ReceiptDisplaySerializer,
    ThirtyPercentWithholdingReceiptSerializer,
)
from core.serializers.DocumentSerializer import (
    ReceiptDocumentDetailSerializer,
)  # ← Ensure this exists

# views.py
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


# views.py
from rest_framework import generics
from django.db.models import Q


class ReceiptListView(generics.ListAPIView):
    """
    GET /api/receipts/
    List all receipts where:
      - The user's company is either the issuer OR receiver
    Ordered by date (newest first).
    """

    serializer_class = ReceiptDisplaySerializer
    # permission_classes = [IsAuthenticated]  # Optional: if you have DRF auth too

    def get_queryset(self):
        user_info = getattr(self.request, "user_info", None)
        if not user_info:
            return Receipt.objects.none()

        user_tin = user_info["tin"]
        company_name = user_info["company_name"]
        print(f"📄 {company_name} is fetching receipts...")

        queryset = (
            Receipt.objects.select_related("issued_by", "issued_to")
            .prefetch_related(
                "items__item",  # ← Critical: pre-load all item data
            )
            .filter(
                Q(issued_by__tin_number=user_tin) | Q(issued_to__tin_number=user_tin)
            )
            .order_by("-receipt_date")
        )

        print(f"✅ Found {queryset.count()} receipts for {company_name}")
        return queryset


class ReceiptDetailView(generics.RetrieveAPIView):
    """
    GET /api/receipts/{id}/
    Retrieve a single receipt with all details.
    """

    queryset = Receipt.objects.select_related("issued_by", "issued_to")
    serializer_class = ReceiptDisplaySerializer
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )


class ThirtyPercentWithholdingReceiptListCreateView(ListCreateAPIView):
    queryset = ThirtyPercentWithholdingReceipt.objects.all()
    serializer_class = ThirtyPercentWithholdingReceiptSerializer
    # permission_classes = [IsAuthenticated]  # Remove if public

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return Response(
            {
                "success": True,
                "message": "30% withholding receipt created successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class ThirtyPercentWithholdingReceiptDetailView(RetrieveUpdateDestroyAPIView):
    queryset = ThirtyPercentWithholdingReceipt.objects.all()
    serializer_class = ThirtyPercentWithholdingReceiptSerializer
    lookup_field = "withholding_receipt_number"  # Optional: lookup by number

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Withholding receipt updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"success": True, "message": "Withholding receipt deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )
