# core/views/draft_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import date, datetime
from django.core.serializers.json import DjangoJSONEncoder
import json

from core.models.contact import Contact
from core.models.Documents import ReceiptDocument
from core.models.DraftReceipt import DraftReceipt
from core.serializers.DraftDataSerializer import DraftDataSerializer


class DraftsView(APIView):
    # core/views/draft_views.py

    def get(self, request):
        """
        GET /api/drafts/ → List all drafts WITH full data
        No need for ?receipt_number=...
        """
        company_tin = getattr(request, 'company_tin', None)
        if not company_tin:
            return Response({"error": "Auth failed"}, status=401)

        try:
            company = Contact.objects.get(tin_number=company_tin)
        except Contact.DoesNotExist:
            return Response({"error": "Company not found"}, status=400)

        # ✅ Load ALL drafts with full data
        drafts = DraftReceipt.objects.filter(
            company=company,
            status='draft'
        ).order_by('-updated_at')

        # ✅ Serialize full draft including .data
        data = [
            {
                "draft_id": str(draft.id),
                "uploaded_document_number": draft.uploaded_document_number,
                "receipt_number": draft.receipt_number or "Not Set",
                "status": draft.status,
                "created_at": draft.created_at,
                "updated_at": draft.updated_at,
                "data": draft.data  # ✅ Include full form data
            }
            for draft in drafts
        ]

        return Response(data, status=200)

    def load_draft_by_receipt_number(self, request, company, receipt_number):
        """Load a specific draft using smart matching"""
        uploaded_doc_num = self.find_uploaded_doc_num(receipt_number, company)
        if not uploaded_doc_num:
            return Response(
                {"error": f"No uploaded document found for '{receipt_number}'"},
                status=404
            )

        draft, created = DraftReceipt.objects.get_or_create(
            company=company,
            uploaded_document_number=uploaded_doc_num,
            defaults={"data": {}, "status": "draft"}
        )

        return Response({
            "draft_id": str(draft.id),
            "uploaded_document_number": draft.uploaded_document_number,
            "receipt_number": draft.receipt_number,
            "data": draft.data,
            "created_at": draft.created_at,
            "updated_at": draft.updated_at,
            "status": draft.status
        }, status=200)

    def list_all_drafts(self, company):
        """Return all active drafts for this company"""
        drafts = DraftReceipt.objects.filter(
            company=company,
            status='draft'
        ).select_related('company').order_by('-updated_at')

        data = [
            {
                "draft_id": str(draft.id),
                "uploaded_document_number": draft.uploaded_document_number,
                "receipt_number": draft.receipt_number or "Not Set",
                "status": draft.status,
                "created_at": draft.created_at,
                "updated_at": draft.updated_at,
                "has_data": bool(draft.data)
            }
            for draft in drafts
        ]

        return Response(data, status=200)

    def patch(self, request):
        """Save draft — preserve exact frontend JSON structure"""
        company_tin = getattr(request, 'company_tin', None)
        if not company_tin:
            return Response({"error": "Auth failed"}, status=401)

        receipt_number = request.data.get("receipt_number")
        if not receipt_number:
            return Response({"error": "receipt_number required"}, status=400)

        try:
            company = Contact.objects.get(tin_number=company_tin)

            uploaded_doc_num = self.find_uploaded_doc_num(receipt_number, company)
            if not uploaded_doc_num:
                return Response(
                    {"error": f"No upload found for '{receipt_number}'"},
                    status=400
                )

            draft, created = DraftReceipt.objects.get_or_create(
                company=company,
                uploaded_document_number=uploaded_doc_num,
                defaults={"data": {}, "status": "draft"}
            )

            # ✅ Validate
            serializer = DraftDataSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=400)

            validated_data = serializer.validated_data

            # ✅ Ensure receipt_date is string
            if 'receipt_date' in validated_data:
                if isinstance(validated_data['receipt_date'], (date, datetime)):
                    validated_data['receipt_date'] = validated_data['receipt_date'].isoformat()

            # ✅ Remove any model objects (just in case)
            for field in ['receipt_category', 'receipt_kind', 'receipt_type', 'receipt_name']:
                validated_data.pop(field, None)

            # ✅ Use DjangoJSONEncoder to clean
            clean_data = json.loads(json.dumps(validated_data, cls=DjangoJSONEncoder))

            # ✅ Save — this becomes the `data` field
            draft.data = clean_data
            draft.receipt_number = receipt_number
            draft.save()

            return Response({"message": "Draft saved"}, status=200)

        except Contact.DoesNotExist:
            return Response({"error": "Company not found"}, status=400)

    def find_uploaded_doc_num(self, receipt_number: str, company: Contact) -> str:
        """Find uploaded document (FS246 → 246)"""
        import re
        match = re.match(r"^([A-Za-z]+)(\d+)$", receipt_number.strip())
        candidates = [receipt_number, receipt_number.upper(), receipt_number.lower()]
        if match:
            candidates.append(match.group(2))  # digits only

        for candidate in candidates:
            try:
                doc = ReceiptDocument.objects.get(
                    main_receipt__receipt_number__iexact=candidate,
                    for_company=company,
                    linked_receipt__isnull=True,
                    status='uploaded'
                )
                return doc.main_receipt.receipt_number
            except ReceiptDocument.DoesNotExist:
                continue
        return None
