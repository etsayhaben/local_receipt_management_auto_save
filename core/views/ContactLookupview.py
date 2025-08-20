# core/views/ContactLookupView.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models.contact import Contact


class ContactLookupView(APIView):
    """
    Lookup contacts by:
    - tin_prefix=123 → returns ALL matching contacts with FULL data
    - tin_number=1234567890 → returns single contact with FULL data
    """
    permission_classes = []  # Change to [IsAuthenticated] if needed

    def get(self, request):
        tin_number = request.query_params.get('tin_number', '').strip()
        tin_prefix = request.query_params.get('tin_prefix', '').strip()

        if not tin_number and not tin_prefix:
            return Response(
                {"error": "Provide 'tin_number' or 'tin_prefix'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle: tin_prefix search (e.g., user typing)
        if tin_prefix:
            if not tin_prefix.isdigit():
                return Response(
                    {"error": "tin_prefix must contain only digits."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 🔽 Get full contact data (name, tin, address)
            contacts = Contact.objects.filter(tin_number__startswith=tin_prefix)

            if not contacts.exists():
                return Response(
                    {"error": "No contacts found with matching TIN prefix."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Serialize full data
            results = [
                {
                    "name": c.name,
                    "tin_number": c.tin_number,
                    "address": c.address
                }
                for c in contacts
            ]
            return Response(results, status=status.HTTP_200_OK)

        # Handle: exact tin_number lookup
        if tin_number:
            if not tin_number.isdigit() or len(tin_number) != 10:
                return Response(
                    {"error": "TIN must be exactly 10 digits."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                contact = Contact.objects.get(tin_number=tin_number)
                # 🔽 Return full data
                return Response({
                    "name": contact.name,
                    "tin_number": contact.tin_number,
                    "address": contact.address
                }, status=status.HTTP_200_OK)
            except Contact.DoesNotExist:
                return Response(
                    {"error": "Contact not found."},
                    status=status.HTTP_404_NOT_FOUND
                )