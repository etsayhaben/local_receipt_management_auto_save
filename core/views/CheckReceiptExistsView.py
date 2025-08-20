# core/views/CheckReceiptExistsView.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models.Receipt import Receipt
from core.models.contact import Contact


class CheckReceiptExistsView(APIView):
    """
    Check if a Receipt with the given receipt_number exists for the authenticated company.
    Uses company_tin from request context (middleware).
    Usage: GET /api/check-receipt-exists/?receipt_number=INV-001
    """
    permission_classes = []  # Or [IsAuthenticated] if not using middleware-only auth

    def get(self, request):
        # Get receipt_number from query params
        receipt_number = request.query_params.get('receipt_number', '').strip()

        # Get company_tin from context (set by middleware)
        company_tin = getattr(request, 'company_tin', None)

        # Validate
        if not receipt_number:
            return Response(
                {"error": "receipt_number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not company_tin:
            return Response(
                {"error": "Authentication failed: company TIN not found."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validate TIN format
        if not company_tin.isdigit() or len(company_tin) != 10:
            return Response(
                {"error": "Invalid company TIN."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find the company (recorded_by)
        try:
            recorded_by = Contact.objects.get(tin_number__iexact=company_tin)
        except Contact.DoesNotExist:
            return Response(
                {"exists": False},  # Safe: no company → no receipt
                status=status.HTTP_200_OK
            )

        # Check if receipt exists for this company
        exists = Receipt.objects.filter(
            receipt_number__iexact=receipt_number,
            recorded_by=recorded_by
        ).exists()

        return Response({"exists": exists}, status=status.HTTP_200_OK)