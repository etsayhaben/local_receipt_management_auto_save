from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from core.models.Documents import MainReceiptDocument, ReceiptDocument, WithholdingReceiptDocument
from core.serializers.DocumentSerializer import (
    DocumentListItemSerializer,
    UploadReceiptSerializer,
    ReceiptDocumentDetailSerializer,
)

# views.py
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny

from core.models.Documents import ReceiptDocument
from core.models.contact import Contact
from core.serializers.DocumentSerializer import UploadReceiptSerializer


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, serializers
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from core.models.Documents import ReceiptDocument
from core.models.contact import Contact
from core.serializers.DocumentSerializer import UploadReceiptSerializer
from core.serializers.ReceiptSerializer import ReceiptSerializer
from core.services.ReceiptService import ReceiptService
from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser


class CreateReceiptView(CreateAPIView):
    serializer_class = ReceiptSerializer
    permission_classes = [AllowAny]  # Handled by middleware

    def create(self, request, *args, **kwargs):
        # 1. Get company TIN from JWT (set by middleware)
        company_tin = request.company_tin

        # 2. Find the Contact with that TIN → this is recorded_by
        try:
            recorded_by = Contact.objects.get(tin_number=company_tin)
        except Contact.DoesNotExist:
            return Response(
                {"error": f"Company with TIN {company_tin} not found. Please register your business."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Validate the receipt data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 4. Create receipt and pass recorded_by
        try:
            receipt = ReceiptService.create_receipt(
                validated_data=serializer.validated_data,
                recorded_by=recorded_by  # ← Passed here
            )
            return Response(
                {
                    "message": "Receipt saved successfully",
                    "receipt_id": receipt.id,
                    "recorded_by_tin": recorded_by.tin_number,
                    "total": float(receipt.total),
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to save receipt: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


# core/views/UploadReceiptDocumentView.py

from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny

from core.models.contact import Contact
from core.serializers.DocumentSerializer import UploadReceiptSerializer

class UploadReceiptDocumentView(CreateAPIView):
    """
    Upload a receipt document with zero input required beyond file.

    - Gets for_company from JWT (request.company_tin)
    - Allows same receipt_number + date for corrections
    - Warns if duplicate detected
    - Blocks only if exact file re-uploaded
    """
    queryset = ReceiptDocument.objects.all()
    serializer_class = UploadReceiptSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        company_tin = getattr(request, 'company_tin', None)
        name=getattr(request,"company_name",None)
        address=getattr(request,"address",None)
        if not company_tin:
            return Response(
                {"error": "Authentication failed: company TIN not found."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ✅ FIX: Get OR CREATE the company contact
        try:
            for_company = Contact.objects.get(tin_number=company_tin)
        except Contact.DoesNotExist:
            # Create a new contact for this TIN
            print(f"Creating new Contact for TIN: {company_tin}")
            for_company = Contact.objects.create(
                tin_number=company_tin,
                name=name,  # You could get this from token if available
                address=address
            )

        serializer = self.get_serializer(
            data=request.data,
            context={'request': request, 'for_company': for_company}
        )
        serializer.is_valid(raise_exception=False)  # ⚠️ Don't raise on warning

        # Capture warning
        warning = getattr(serializer, 'warning', None)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            document = serializer.save()
            response_data = {
                "message": "Receipt document uploaded successfully",
                "document_id": document.id,
                "for_company_tin": company_tin,
                "uploaded_by_tin": company_tin,
                "notes": document.notes,
                "status": document.status,
                "uploaded_at": document.uploaded_at,  # ← FIXED: Was 'created_at'
                "file_url": document.main_receipt.main_receipt.url if document.main_receipt.main_receipt else None,
                "main_receipt_id": document.main_receipt.id,
                "withholding_receipt_id": document.withholding_receipt.id if document.withholding_receipt else None,
            }
            if warning:
                response_data["warning"] = warning["warning"]

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"Upload failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
class ReceiptDocumentListView(ListAPIView):
    """
    View to list all uploaded receipt documents.
    """

    queryset = ReceiptDocument.objects.select_related(
        "main_receipt", "withholding_receipt"
    )
    serializer_class = ReceiptDocumentDetailSerializer
    permission_classes = [AllowAny]


from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotFound
from core.models.Documents import ReceiptDocument
from core.serializers.DocumentSerializer import ReceiptDocumentDetailSerializer


class ReceiptDocumentDetailView(RetrieveAPIView):
    """
    View to retrieve a specific receipt document by receipt_number.
    URL: /api/get-documents/<receipt_number>/
    """
    serializer_class = ReceiptDocumentDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        receipt_number = self.kwargs.get("receipt_number")
        try:
            return ReceiptDocument.objects.select_related(
                "main_receipt", "withholding_receipt"
            ).get(receipt_number=receipt_number)
        except ReceiptDocument.DoesNotExist:
            raise NotFound(f"ReceiptDocument with receipt_number '{receipt_number}' not found.")


from django.db.models import Q, Value
from django.db.models.functions import Cast
from rest_framework import generics, pagination, status
from rest_framework.response import Response
from rest_framework import serializers
from django.core.paginator import Paginator
from django.db import models  # Import models for field types

# Make sure these imports match your actual model locations
from core.models.contact import Contact
# core/serializers/DocumentSerializer.py
class DocumentListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    receipt_number = serializers.CharField(allow_null=True)
    withholding_receipt_number = serializers.CharField(allow_null=True)
    company_tin = serializers.CharField()

    uploaded_at = serializers.DateTimeField()
    status = serializers.CharField()

    # Main receipt
    main_file_url = serializers.URLField(allow_null=True)
    main_filename = serializers.CharField(allow_null=True)
    main_content_type = serializers.CharField(allow_null=True)

    # Main attachment
    main_attachment_url = serializers.URLField(allow_null=True)
    main_attachment_filename = serializers.CharField(allow_null=True)
    main_attachment_content_type = serializers.CharField(allow_null=True)
    has_main_attachment = serializers.BooleanField()

    # Withholding receipt
    withholding_file_url = serializers.URLField(allow_null=True)
    withholding_filename = serializers.CharField(allow_null=True)
    withholding_content_type = serializers.CharField(allow_null=True)

    # Withholding attachment
    withholding_attachment_url = serializers.URLField(allow_null=True)
    withholding_attachment_filename = serializers.CharField(allow_null=True)
    withholding_attachment_content_type = serializers.CharField(allow_null=True)
    has_withholding_attachment = serializers.BooleanField()

class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import datetime

class DocumentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DocumentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
# core/views/DocumentListView.py
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
import logging

from core.models.contact import Contact
from core.models.Documents import ReceiptDocument

logger = logging.getLogger(__name__)


class DocumentListView(generics.GenericAPIView):
    """
    GET endpoint to list all ReceiptDocument entries as one row per transaction,
    including both main and withholding receipts, attachment URLs, and summary.
    """
    serializer_class = DocumentListItemSerializer
    pagination_class = DocumentPagination

    def get(self, request, *args, **kwargs):
        company_tin = getattr(request, 'company_tin', None)
        if not company_tin:
            return Response(
                {"error": "Authentication failed: company TIN not found."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            company = Contact.objects.get(tin_number=company_tin)
        except Contact.DoesNotExist:
            logger.info(f"Creating new Contact for TIN: {company_tin}")
            company = Contact.objects.create(
                tin_number=company_tin,
                name="New Company",
                address="Address not provided"
            )

        # Get filters
        status_filter = request.query_params.get('status', None)
        search = request.query_params.get('search', None)

        start_date = None
        end_date = None
        if 'start_date' in request.query_params:
            try:
                start_date = datetime.fromisoformat(request.query_params['start_date'])
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid start_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM)."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if 'end_date' in request.query_params:
            try:
                end_date = datetime.fromisoformat(request.query_params['end_date'])
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid end_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM)."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Base queryset: one row per ReceiptDocument
        receipt_docs = ReceiptDocument.objects.filter(
            for_company=company
        ).select_related(
            'main_receipt',
            'withholding_receipt'
        ).order_by('-uploaded_at')

        # Apply filters
        if status_filter:
            receipt_docs = receipt_docs.filter(status=status_filter)

        if start_date or end_date:
            if start_date and end_date:
                receipt_docs = receipt_docs.filter(uploaded_at__range=(start_date, end_date))
            elif start_date:
                receipt_docs = receipt_docs.filter(uploaded_at__gte=start_date)
            elif end_date:
                receipt_docs = receipt_docs.filter(uploaded_at__lte=end_date)

        if search:
            receipt_docs = receipt_docs.filter(
                Q(main_receipt__receipt_number__icontains=search) |
                Q(withholding_receipt__withholding_receipt_number__icontains=search) |
                Q(notes__icontains=search)
            )

        # Convert to list of dicts (for serialization)
        documents = []
        for doc in receipt_docs:
            # Get main receipt data
            main = doc.main_receipt
            withholding = doc.withholding_receipt

            item = {
                "id": doc.id,
                "receipt_number": main.receipt_number if main else None,
                "withholding_receipt_number": withholding.withholding_receipt_number if withholding else None,
                "company_tin": company.tin_number,
                "uploaded_at": doc.uploaded_at,
                "status": doc.status,

                # Main receipt
                "main_file_url": self.get_file_url(main.main_receipt if main else None),
                "main_filename": main.main_receipt_filename if main else None,
                "main_content_type": main.main_receipt_content_type if main else None,

                # Main attachment
                "main_attachment_url": self.get_file_url(main.attachment if main else None),
                "main_attachment_filename": main.attachment_filename if main else None,
                "main_attachment_content_type": main.attachment_content_type if main else None,
                "has_main_attachment": bool(main.attachment) if main else False,

                # Withholding receipt
                "withholding_file_url": self.get_file_url(withholding.withholding_receipt if withholding else None),
                "withholding_filename": withholding.withholding_receipt_filename if withholding else None,
                "withholding_content_type": withholding.withholding_receipt_content_type if withholding else None,

                # Withholding attachment
                "withholding_attachment_url": self.get_file_url(withholding.withholding_attachment if withholding else None),
                "withholding_attachment_filename": withholding.withholding_attachment_filename if withholding else None,
                "withholding_attachment_content_type": withholding.withholding_attachment_content_type if withholding else None,
                "has_withholding_attachment": bool(withholding.withholding_attachment) if withholding else False,
            }
            documents.append(item)

        # Sort by uploaded_at (newest first)
        documents.sort(key=lambda x: x['uploaded_at'], reverse=True)

        # Paginate
        page = self.paginate_queryset(documents)
        serializer = self.get_serializer(page, many=True)
        response = self.get_paginated_response(serializer.data)

        # Add summary
        response.data['summary'] = {
            'total_transactions': len(documents),
            'with_main_receipt': len([d for d in documents if d['main_file_url']]),
            'with_withholding_receipt': len([d for d in documents if d['withholding_file_url']]),
            'statuses': {
                'uploaded': len([d for d in documents if d['status'] == 'uploaded']),
                'processed': len([d for d in documents if d['status'] == 'processed']),
                'rejected': len([d for d in documents if d['status'] == 'rejected'])
            },
            'has_attachments': {
                'main': len([d for d in documents if d['has_main_attachment']]),
                'withholding': len([d for d in documents if d['has_withholding_attachment']])
            }
        }

        return response

    def get_file_url(self, file_field):
        """Safely get file URL"""
        if file_field and hasattr(file_field, 'url'):
            try:
                return file_field.url
            except ValueError:
                return None
        return None