# core/views/receipt_delete.py

from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from core.models.Receipt import Receipt

# core/views/receipt_update_by_number.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.serializers.ReceiptSerializer import ReceiptUpdateSerializer


class ReceiptDeleteView(APIView):
    """
    API Endpoint: DELETE /api/receipts/delete/?receipt_number=RC-2025-001
    Deletes a receipt and its related lines by receipt_number.
    """

    def delete(self, request, *args, **kwargs):
        receipt_number = request.query_params.get("receipt_number", "").strip()

        if not receipt_number:
            return Response(
                {"error": "Missing 'receipt_number' in query parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the receipt (case-insensitive)
        receipt = get_object_or_404(Receipt, receipt_number__iexact=receipt_number)

        # Capture data before deletion (for response/logging)
        deleted_data = {
            "receipt_number": receipt.receipt_number,
            "issued_to": receipt.issued_to.name if receipt.issued_to else None,
            "total_lines": receipt.items.count() if hasattr(receipt, "items") else 0,
        }

        # Delete the receipt → Django will auto-delete related ReceiptLine (if on_delete=models.CASCADE)
        receipt.delete()

        return Response(
            {
                "message": "Receipt and associated lines deleted successfully.",
                "deleted": deleted_data,
            },
            status=status.HTTP_200_OK,  # 200 OK is fine; 204 No Content also acceptable
        )

        # core/views/receipt_update_by_number.py


# core/views/receipt_update_by_number.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from core.models.Receipt import Receipt


@method_decorator(csrf_exempt, name='dispatch')
class ReceiptUpdateByNumberView(APIView):
    """
    PATCH /api/receipts/update-by-number/?receipt_number=RC-123
    Updates a receipt by its receipt_number (case-insensitive).
    Supports partial updates.
    """

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        raw_number = request.query_params.get("receipt_number", "").strip()
        if not raw_number:
            return Response(
                {"error": "Missing 'receipt_number' in query parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Clean quotes: "RC-123" → RC-123
        receipt_number = raw_number.strip('"\'')
        
        # Case-insensitive lookup
        receipt = get_object_or_404(Receipt, receipt_number__iexact=receipt_number)

        serializer = ReceiptUpdateSerializer(
            instance=receipt,
            data=request.data,
            partial=True  # Allow partial update
        )

        if serializer.is_valid():
            try:
                updated_receipt = serializer.save()
                return Response({
                    "message": "Receipt updated successfully.",
                    "data": ReceiptUpdateSerializer(updated_receipt).data
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    "error": "Failed to save receipt.",
                    "details": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "error": "Validation failed.",
            "details": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)