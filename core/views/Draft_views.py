# core/views/draft_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

from django.db import transaction

# Models

from core.models.contact import Contact
from core.models.Documents import ReceiptDocument, MainReceiptDocument
from local_receipt_management_system.core.models.DraftReceipt import DraftReceipt
from local_receipt_management_system.core.serializers.DraftDataSerializer import DraftDataSerializer



logger = logging.getLogger(__name__)


class DraftsView(APIView):
    """
    Unified /api/drafts/ endpoint:
    - GET: Load draft by receipt_number
    - PATCH: Save draft data (autosave)
    """

    def get(self, request):
        """
        GET /api/drafts/?receipt_number=FS246
        Load draft for this receipt number.
        Auto-finds uploaded document (FS246 → 246)
        """
        company_tin = getattr(request, 'company_tin', None)
        if not company_tin:
            return Response(
                {"error": "Authentication failed: company TIN not found."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        receipt_number = request.query_params.get("receipt_number")
        if not receipt_number:
            return Response(
                {"error": "receipt_number is required as query parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            company = Contact.objects.get(tin_number=company_tin)

            # 🔍 Step 1: Find uploaded document using smart matching
            uploaded_doc_num = self.find_matching_uploaded_document_number(receipt_number, company)
            if not uploaded_doc_num:
                return Response(
                    {"error": f"No uploaded document found for '{receipt_number}'"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 🔗 Step 2: Get or create draft using uploaded_document_number
            draft, created = DraftReceipt.objects.get_or_create(
                company=company,
                uploaded_document_number=uploaded_doc_num,
                defaults={
                    "data": {},
                    "status": "draft",
                    "revision": 0
                }
            )

            return Response({
                "draft_id": str(draft.id),
                "uploaded_document_number": draft.uploaded_document_number,
                "receipt_number": draft.receipt_number,
                "data": draft.data,
                "revision": draft.revision,
                "created_at": draft.created_at,
                "updated_at": draft.updated_at,
                "status": draft.status
            }, status=status.HTTP_200_OK)

        except Contact.DoesNotExist:
            return Response(
                {"error": f"Company with TIN {company_tin} not found."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Unexpected error loading draft")
            return Response(
                {"error": "Failed to load draft"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request):
        """
        PATCH /api/drafts/
        Save draft data (autosave).
        Expects:
        {
          "receipt_number": "FS246",
          "expected_revision": 5,
          "data": { ... }
        }
        """
        company_tin = getattr(request, 'company_tin', None)
        if not company_tin:
            return Response(
                {"error": "Authentication failed"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Parse input
        receipt_number = request.data.get("receipt_number")
        expected_revision = request.data.get("expected_revision")
        form_data = request.data.get("data", {})

        if not receipt_number:
            return Response(
                {"error": "receipt_number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            company = Contact.objects.get(tin_number=company_tin)

            # 🔍 Step 1: Resolve uploaded document number (FS246 → 246)
            uploaded_doc_num = self.find_matching_uploaded_document_number(receipt_number, company)
            if not uploaded_doc_num:
                return Response(
                    {"error": f"No uploaded document found for '{receipt_number}'"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 🔗 Step 2: Get draft
            try:
                draft = DraftReceipt.objects.get(
                    company=company,
                    uploaded_document_number=uploaded_doc_num
                )
            except DraftReceipt.DoesNotExist:
                return Response(
                    {"error": "Draft not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 🔒 Step 3: Conflict detection
            if expected_revision is not None and draft.revision != expected_revision:
                return Response({
                    "error": "Draft was modified by another user",
                    "current": {
                        "revision": draft.revision,
                        "data": draft.data
                    }
                }, status=status.HTTP_409_CONFLICT)

            # ✅ Step 4: Validate draft data
            serializer = DraftDataSerializer(data=form_data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # ✅ Step 5: Save draft
            with transaction.atomic():
                draft.data = {**draft.data, **serializer.validated_data}
                draft.receipt_number = receipt_number
                draft.revision += 1
                draft.save()

            return Response({"revision": draft.revision}, status=status.HTTP_200_OK)

        except Contact.DoesNotExist:
            return Response(
                {"error": "Company not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Failed to save draft")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def find_matching_uploaded_document_number(self, receipt_number: str, company: Contact) -> str:
        """
        Given receipt_number (e.g., FS246), find the corresponding uploaded document.
        Returns the uploaded_document_number (e.g., "246")
        """
        import re

        # Try to split into prefix and digits: FS246 → FS, 246
        match = re.match(r"^([A-Za-z]+)(\d+)$", receipt_number.strip())
        if match:
            prefix, doc_digits = match.groups()
            candidates = [
                receipt_number,
                receipt_number.upper(),
                receipt_number.lower(),
                doc_digits,
            ]
        else:
            candidates = [receipt_number]

        # Search for ReceiptDocument that:
        # - Has main_receipt.receipt_number matching candidate
        # - Belongs to this company
        # - Is unprocessed
        for candidate in candidates:
            try:
                receipt_document = ReceiptDocument.objects.select_related('main_receipt').get(
                    main_receipt__receipt_number__iexact=candidate,
                    for_company=company,
                    linked_receipt__isnull=True,
                    status='uploaded'
                )
                return receipt_document.main_receipt.receipt_number
            except ReceiptDocument.DoesNotExist:
                continue

        return None