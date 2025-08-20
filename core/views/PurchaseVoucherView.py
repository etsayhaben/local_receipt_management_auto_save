from rest_framework.generics import CreateAPIView
from core.models.PurchaseVoucher import PurchaseVoucher
from core.serializers.PurchaseVoucherSerializer import PurchaseVoucherSerializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class CreatePurchaseVoucherView(CreateAPIView):
    queryset = PurchaseVoucher.objects.all()
    serializer_class = PurchaseVoucherSerializer

    @swagger_auto_schema(
        operation_summary="Create Purchase Voucher with File Uploads",
        operation_description="""
            Upload a new purchase voucher with optional document and attachment.
            Files are stored as binary data in the database.
            Use `multipart/form-data` for file uploads.
        """,
        request_body=PurchaseVoucherSerializer,  # File fields will now be recognized
        consumes=["multipart/form-data"],
        responses={
            201: openapi.Response(
                description="Purchase voucher created successfully",
                schema=PurchaseVoucherSerializer,
            ),
            400: "Validation error",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
