# core/urls.py
from django.urls import path
from core import views
from core.views import search_receipts
# from core.views import generat_receipt_pdf
from core.views.ContactLookupview import ContactLookupView
from core.views.Receipt_delete import ReceiptDeleteView, ReceiptUpdateByNumberView
from core.views.RegiserandDisplayDocumentsView import (
    DocumentListView,
    ReceiptDocumentDetailView,
    ReceiptDocumentListView,
    UploadReceiptDocumentView,
)
from core.views.Register import CreateReceiptView
from core.views.PurchaseVoucherView import CreatePurchaseVoucherView
from core.views.ReceiptDisplayView import (
    ReceiptListView,
    ReceiptDetailView,
    ThirtyPercentWithholdingReceiptDetailView,
    ThirtyPercentWithholdingReceiptListCreateView,
)
from core.views.Search import SearchView
# from core.views.generat_receipt_pdf import generate_receipts_pdf
from core.views.CheckReceiptExistsView import CheckReceiptExistsView
from core.views.lookupviews import (
    ReceiptKindListAPIView,
    ReceiptKindCreateView,
    ReceiptNameListAPIView,
    ReceiptNameCreateView,
    ReceiptCategoryListAPIView,
    ReceiptCategoryCreateView,
    ReceiptTypeListAPIView,
    ReceiptTypeCreateView,
)
from core.views.Draft_views import DraftsView

urlpatterns = [
    path("create-receipt", CreateReceiptView.as_view(), name="create-receipt"),
    path(
        "create-purchase-voucher",
        CreatePurchaseVoucherView.as_view(),
        name="create_purchase_voucher",
    ),
    # path(
    #     "receipt/pdf/",
    #     generat_receipt_pdf.generate_receipts_pdf,
    #     name="receipt_pdf",
    # ),
    path(
        "upload-receipt-documents",
        UploadReceiptDocumentView.as_view(),
        name="upload-document",
    ),
    path("receipts", ReceiptListView.as_view(), name="receipt-list"),
    path("receipts/<int:id>", ReceiptDetailView.as_view(), name="receipt-detail"),
    # Lookup data
    path("receipt-kinds", ReceiptKindListAPIView.as_view(), name="receipt-kind-list"),
    path(
        "receipt-kinds/new",
        ReceiptKindCreateView.as_view(),
        name="receipt-kind-create",
    ),
    path('check-receipt-exists/', CheckReceiptExistsView.as_view(), name='check-receipt-exists'),
    path('drafts', DraftsView.as_view(), name='drafts'),

    path(
        "receipt-document/<int:id>/",
        ReceiptDocumentDetailView.as_view(),
        name="receipt-document-detail",
    ),
    path(
        "receipts/delete",
        ReceiptDeleteView.as_view(),
        name="receipt-delete-by-number",
    ),
    path(
        "receipts/update-by-receipt-number/",
        ReceiptUpdateByNumberView.as_view(),
        name="receipt-update-by-number",
    ),
    path(
        "30percent-withholding/",
        ThirtyPercentWithholdingReceiptListCreateView.as_view(),
        name="withholding-list-create",
    ),
    path(
        "30percent-withholding/<str:withholding_receipt_number>/",
        ThirtyPercentWithholdingReceiptDetailView.as_view(),
        name="withholding-detail",
    ),
    path(
        "RetriveImportExportRelatedReceipts/",
        SearchView.as_view(),
        name="search-items-by-declaration-number",
    ),
    path(
        "get-documents",
        DocumentListView.as_view(),
        name="retriving reciept documetns",
    ),
    path(
        "receipts/search/",
        search_receipts.ReceiptSearchView.as_view(),
        name="search_receipts",
    ),
    # path(
    #     "receipts/export/pdf/",
    #     search_receipts.export_receipts_pdf,
    #     name="export_receipts_pdf",
    # ),
    path(
        "get-documents/<str:receipt_number>/",
        ReceiptDocumentDetailView.as_view(),
        name="get-document-by-receipt-number",
    ),
    path("receipt-names/", ReceiptNameListAPIView.as_view(), name="receipt-name-list"),
    path(
        "receipt-names/new/",
        ReceiptNameCreateView.as_view(),
        name="receipt-name-create",
    ),
    path(
        "receipt-categories/",
        ReceiptCategoryListAPIView.as_view(),
        name="receipt-category-list",
    ),
    path(
        "receipt-categories/new/",
        ReceiptCategoryCreateView.as_view(),
        name="receipt-category-create",
    ),
     path('contacts/lookup/', ContactLookupView.as_view(), name='contact-lookup'),
    path(
        "upload-receipt-documents",
        UploadReceiptDocumentView.as_view(),
        name="upload-document",
    ),
    path("receipt-types/", ReceiptTypeListAPIView.as_view(), name="receipt-type-list"),
    path(
        "receipt-types/new/",
        ReceiptTypeCreateView.as_view(),
        name="receipt-type-create",
    ),
]
