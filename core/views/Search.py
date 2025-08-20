# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from core.serializers.ReceiptLineSearchSerializer import ReceiptLineSearchSerializer
from core.models.Receipt import ReceiptLine

# 🔽 Import for Swagger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class SearchView(APIView):
    """
    Retrieve all receipt lines that have a non-empty declaration number.
    """

    @swagger_auto_schema(
        operation_summary="Get All Receipt Lines with Declaration Numbers",
        operation_description="""
            Retrieve all receipt line items where the associated item's 
            declaration number is set (not null or empty).
        """,
        responses={
            200: openapi.Response(
                description="List of receipt lines with declaration numbers (deduplicated by item)",
                schema=ReceiptLineSearchSerializer(many=True),
            ),
            404: "Not Found - No items have declaration numbers",
        },
    )
    def get(self, request):
        """
        Handle GET request to fetch all receipt lines that have declaration numbers.
        """
        # Query: filter lines where item.declaration_number is not null and not empty
        lines = ReceiptLine.objects.filter(
            ~Q(item__declaration_number__isnull=True),
            ~Q(item__declaration_number__exact=""),
        ).select_related("item", "receipt", "receipt__issued_to")

        if not lines.exists():
            return Response(
                {"message": "No items found with declaration numbers."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Deduplicate by item.id
        seen = set()
        unique_lines = []
        for line in lines:
            if line.item.id not in seen:
                unique_lines.append(line)
                seen.add(line.item.id)

        # Serialize the data
        serializer = ReceiptLineSearchSerializer(unique_lines, many=True)

        return Response(
            {"count": len(serializer.data), "data": serializer.data},
            status=status.HTTP_200_OK,
        )



