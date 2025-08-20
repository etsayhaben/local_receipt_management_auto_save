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
        # 1. DEBUG: Check if middleware set company_tin
        print(f"Request company_tin: {getattr(request, 'company_tin', None)}")
        
        # 2. Get company TIN from JWT (set by middleware)
        company_tin = getattr(request, 'company_tin', None)
        
        if not company_tin:
            # DEBUG: Check Authorization header
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            print(f"Authorization header: {auth_header}")
            return Response(
                {"error": "Authentication failed: company TIN not found in token."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 3. DEBUG: Check all Contacts
        print("All Contacts in database:")
        for contact in Contact.objects.all():
            print(f"- ID: {contact.id}, TIN: {contact.tin_number}, Name: {contact.name}")
        
        # 4. Find the Contact with that TIN → this is recorded_by
        try:
            recorded_by = Contact.objects.get(tin_number=company_tin)
            print(f"Found Contact: {recorded_by.id}, {recorded_by.name}, {recorded_by.tin_number}")
        except Contact.DoesNotExist:
            print(f"Contact with TIN {company_tin} not found")
            return Response(
                {"error": f"Company with TIN {company_tin} not found in system. Please register your business."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            print(f"Error finding Contact: {str(e)}")
            return Response(
                {"error": f"Database error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 5. DEBUG: Check serializer context
        print("Passing to serializer context:", {'recorded_by': recorded_by})
        
        # 6. Validate the receipt data
        serializer = self.get_serializer(
            data=request.data,
            context={'recorded_by': recorded_by}  # CRITICAL: Must pass this
        )
        
        # 7. DEBUG: Check if serializer has context
        print("Serializer context:", serializer.context)
        
        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            receipt = serializer.save()
            return Response({
                "message": "Receipt saved successfully",
                "receipt_id": receipt.id,
                "recorded_by_tin": recorded_by.tin_number,
                "total": float(receipt.total),
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(f"Error saving receipt: {str(e)}")
            return Response(
                {"error": f"Failed to save receipt: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )