# from django.core.cache import cache
# from django.http import HttpResponse
# from django.template.loader import render_to_string
# from django.utils.dateparse import parse_date
# from django.utils import timezone
# from django.db.models import Q, Prefetch

# from core.models.Receipt import Receipt, ReceiptLine
# from core.serializers.ReceiptDisplaySerializer import ReceiptDisplaySerializer


# def generate_receipts_pdf(request):
#     # Build a cache key unique to the current query parameters
#     cache_key = "receipt_pdf_" + request.GET.urlencode()

#     # Try to get cached data
#     cached_data = cache.get(cache_key)

#     if cached_data:
#         data = cached_data
#     else:
#         # No cached data, query database with filters
#         receipts = Receipt.objects.prefetch_related(
#             Prefetch("items", queryset=ReceiptLine.objects.all())
#         )

#         # Parse filters from query params
#         from_date = request.GET.get("from_date")
#         to_date = request.GET.get("to_date")
#         issued_by = request.GET.get("issued_by")
#         issued_to = request.GET.get("issued_to")
#         category = request.GET.get("category")
#         receipt_number = request.GET.get("receipt_number")
#         query = request.GET.get("query")

#         filters = {}

#         if from_date:
#             dt = parse_date(from_date)
#             if dt:
#                 filters["receipt_date__gte"] = dt

#         if to_date:
#             dt = parse_date(to_date)
#             if dt:
#                 filters["receipt_date__lte"] = dt

#         if issued_by:
#             filters["issued_by__name__icontains"] = issued_by

#         if issued_to:
#             filters["issued_to__name__icontains"] = issued_to

#         if category:
#             filters["receipt_category__name__icontains"] = category

#         if receipt_number:
#             filters["receipt_number__icontains"] = receipt_number

#         if query:
#             receipts = receipts.filter(
#                 Q(receipt_number__icontains=query)
#                 | Q(issued_by__name__icontains=query)
#                 | Q(issued_to__name__icontains=query)
#                 | Q(receipt_category__name__icontains=query)
#             ).filter(**filters)
#         else:
#             receipts = receipts.filter(**filters)

#         serializer = ReceiptDisplaySerializer(receipts, many=True)

#         data = [
#             {
#                 "receipt_date": r["receipt_date"],
#                 "receipt_number": r["receipt_number"],
#                 "issued_by": r["issued_by_details"]["name"],
#                 "issued_to": r["issued_to_details"]["name"],
#                 "category": r["receipt_category"],
#                 "total": r["total"],
#                 "is_vat_expired": False,  # Add your logic if needed
#             }
#             for r in serializer.data
#         ]

#         # Cache serialized data for 10 minutes (600 seconds)
#         cache.set(cache_key, data, timeout=600)

#     context = {
#         "title": "Receipts Report",
#         "generated_at": timezone.now(),
#         "data": {
#             "count": len(data),
#             "data": data,
#         },
#         "query_params": request.GET.urlencode(),
#     }

#     html_string = render_to_string("pdf/receipt_report.html", context)

#     response = HttpResponse(content_type="application/pdf")
#     response["Content-Disposition"] = "attachment; filename=receipt_report.pdf"
#     HTML(string=html_string).write_pdf(target=response)

#     return response
