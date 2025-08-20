from decimal import Decimal
from datetime import datetime
from functools import reduce
from django.db.models import (
    Count,
    Sum,
    Case,
    When,
    DecimalField,
    Value,
    CharField,
    F,
    Q,
)
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import operator

from core.models.Receipt import Receipt


class ReceiptSearchView(APIView):
    """
    API Endpoint: GET /api/receipts/search/
    Supports filtering, grouping, and searching across Receipt model.
    """

    def get(self, request, *args, **kwargs):
        # Extract query parameters
        query = request.query_params.get("query", "").strip()
        group_by = request.query_params.get("group_by")
        receipt_number = request.query_params.get("receipt_number")
        category = request.query_params.get("category")
        kind = request.query_params.get("kind")
        name = request.query_params.get("name")
        receipt_type = request.query_params.get("type")
        issued_to = request.query_params.get("issued_to")
        issued_by = request.query_params.get("issued_by")
        calendar_type = request.query_params.get("calendar_type")
        is_vat_expired = request.query_params.get("is_vat_expired")
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        tax_type = request.query_params.get("tax_type")  # New filter for tax_type

        # Start with all receipts
        receipts = Receipt.objects.select_related(
            "receipt_category",
            "receipt_kind",
            "receipt_name",
            "receipt_type",
            "issued_to",
            "issued_by",
        ).all()

        # === Apply Filters ===
        if receipt_number:
            receipts = receipts.filter(receipt_number__iexact=receipt_number)

        if category:
            categories = [cat.strip() for cat in category.split(",") if cat.strip()]
            if categories:
                q_objects = reduce(
                    operator.or_,
                    (Q(receipt_category__name__iexact=cat) for cat in categories),
                )
                receipts = receipts.filter(q_objects)

        if kind:
            receipts = receipts.filter(receipt_kind__name__iexact=kind)

        if name:
            receipts = receipts.filter(receipt_name__name__iexact=name)

        if receipt_type:
            receipts = receipts.filter(receipt_type__name__iexact=receipt_type)

        if issued_to:
            receipts = receipts.filter(issued_to__name__icontains=issued_to)

        if issued_by:
            receipts = receipts.filter(issued_by__name__icontains=issued_by)

        if calendar_type:
            receipts = receipts.filter(calendar_type=calendar_type)

        if from_date:
            receipts = receipts.filter(receipt_date__gte=from_date)

        if to_date:
            receipts = receipts.filter(receipt_date__lte=to_date)

        if is_vat_expired == "true":
            receipts = receipts.filter(expired_vat__gt=Decimal("0.00"))
        elif is_vat_expired == "false":
            receipts = receipts.filter(expired_vat=Decimal("0.00"))

        # Filter by tax_type on related items if requested
        if tax_type:
            receipts = receipts.filter(items__tax_type__iexact=tax_type).distinct()

        # Global search (unless receipt_number was used specifically)
        if query and not receipt_number:
            receipts = receipts.filter(
                Q(receipt_number__icontains=query)
                | Q(receipt_category__name__icontains=query)
                | Q(receipt_kind__name__icontains=query)
                | Q(receipt_name__name__icontains=query)
                | Q(issued_to__name__icontains=query)
                | Q(issued_by__name__icontains=query)
                | Q(reason_of_receiving__icontains=query)
            )

        # === Handle Grouping ===
        if group_by:
            response_data = self.handle_grouping(receipts, group_by)
            if isinstance(response_data, dict) and "error" in response_data:
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            return Response(response_data)

        # === Default: Serialize Full Receipt List ===
        results = []
        for r in receipts:
            items_qs = r.items.all()
            tax_type_filter = request.query_params.get("tax_type")
            if tax_type_filter:
                items_qs = items_qs.filter(tax_type__iexact=tax_type_filter)

            subtotal = sum(line.subtotal for line in items_qs)
            tax = sum(line.tax_amount for line in items_qs)
            total = subtotal + tax
            items_data = []
            for item in items_qs:
                items_data.append(
                    {
                        "item_code": item.item.item_code,
                        "item_description": item.item.item_description,
                        "quantity": float(item.quantity),
                        "unit_cost": float(item.item.unit_cost),
                        "subtotal": float(item.subtotal),
                        "tax_type": item.item.tax_type,
                        "tax_amount": float(item.tax_amount),
                        "total":float(item.tax_amount +item.subtotal)
                        
                    }
                )

            results.append(
                {
                    "receipt_number": r.receipt_number,
                    "receipt_date": r.receipt_date,
                    "calendar_type": r.get_calendar_type_display(),
                    "issued_by": r.issued_by.name,
                    "issued_to": r.issued_to.name,
                    "category": r.receipt_category.name if r.receipt_category else None,
                    "kind": r.receipt_kind.name,
                    "name": r.receipt_name.name,
                    "type": r.receipt_type.name,
                    "subtotal": float(subtotal),
                    "tax": float(tax),
                    "total": float(total),
                    "claimable_vat": float(r.claimable_vat),
                    "non_claimable_vat": float(r.non_claimable_vat),
                    "is_vat_expired": r.is_vat_expired,
                    "reason": r.reason_of_receiving,
                    "created_at": r.created_at,
                    "items": items_data,
                }
            )

        return Response(
            {
                "grouped": False,
                "count": len(results),
                "data": results,
            }
        )

    def handle_grouping(self, receipts, group_by):
        """Handles dynamic grouping using database-level calculations."""
        group_mapping = {
            "category": "receipt_category__name",
            "kind": "receipt_kind__name",
            "name": "receipt_name__name",
            "type": "receipt_type__name",
            "issued_to": "issued_to__name",
            "issued_by": "issued_by__name",
            "calendar_type": "calendar_type",
            "month": "receipt_date__month",
            "year": "receipt_date__year",
        }

        # Special VAT status grouping
        if group_by == "vat_status":
            data = (
                receipts.annotate(
                    vat_group=Case(
                        When(expired_vat__gt=0, then=Value("Expired")),
                        default=Value("Claimable"),
                        output_field=CharField(),
                    )
                )
                .values("vat_group")
                .annotate(
                    count=Count("id"),
                    total_amount=Sum(
                        (F("items__quantity") * F("items__unit_cost"))
                        - F("items__discount_amount")
                        + Case(
                            When(
                                items__tax_type__iexact="VAT",
                                then=F("items__tax_amount"),
                            ),
                            default=Value(0),
                            output_field=DecimalField(),
                        )
                        + Case(
                            When(
                                items__tax_type__iexact="TOT",
                                then=F("items__tax_amount"),
                            ),
                            default=Value(0),
                            output_field=DecimalField(),
                        )
                        + Case(
                            When(
                                ~Q(items__tax_type__iexact="VAT")
                                & ~Q(items__tax_type__iexact="TOT"),
                                then=F("items__tax_amount"),
                            ),
                            default=Value(0),
                            output_field=DecimalField(),
                        ),
                    ),
                    total_vat=Sum(
                        Case(
                            When(
                                items__tax_type__iexact="VAT",
                                then=F("items__tax_amount"),
                            ),
                            default=Value(0),
                            output_field=DecimalField(),
                        )
                    )
                    + Sum(
                        Case(
                            When(
                                items__tax_type__iexact="TOT",
                                then=F("items__tax_amount"),
                            ),
                            default=Value(0),
                            output_field=DecimalField(),
                        )
                    )
                    + Sum(
                        Case(
                            When(
                                ~Q(items__tax_type__iexact="VAT")
                                & ~Q(items__tax_type__iexact="TOT"),
                                then=F("items__tax_amount"),
                            ),
                            default=Value(0),
                            output_field=DecimalField(),
                        )
                    ),
                    claimable_vat=Sum(
                        Case(
                            When(
                                expired_vat=0,
                                then=F("items__tax_amount"),
                            ),
                            default=Value(0),
                            output_field=DecimalField(),
                        )
                    ),
                    expired_vat=Sum("expired_vat"),
                )
                .values(
                    "vat_group",
                    "count",
                    "total_amount",
                    "total_vat",
                    "claimable_vat",
                    "expired_vat",
                )
            )
            return {
                "grouped": True,
                "group_by": "vat_status",
                "data": list(data),
            }

        # Normal grouping
        field = group_mapping.get(group_by)
        if not field:
            return {
                "error": f"Invalid group_by field: '{group_by}'. "
                f"Allowed: {list(group_mapping.keys()) + ['vat_status']}"
            }

        annotated = receipts.values(field).annotate(
            count=Count("id"),
            total_amount=Sum(
                (F("items__quantity") * F("items__unit_cost"))
                - F("items__discount_amount")
                + Case(
                    When(items__tax_type__iexact="VAT", then=F("items__tax_amount")),
                    default=Value(0),
                    output_field=DecimalField(),
                )
                + Case(
                    When(items__tax_type__iexact="TOT", then=F("items__tax_amount")),
                    default=Value(0),
                    output_field=DecimalField(),
                )
                + Case(
                    When(
                        ~Q(items__tax_type__iexact="VAT")
                        & ~Q(items__tax_type__iexact="TOT"),
                        then=F("items__tax_amount"),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                ),
            ),
            total_subtotal=Sum(
                (F("items__quantity") * F("items__unit_cost"))
                - F("items__discount_amount")
            ),
            total_vat=Sum(
                Case(
                    When(items__tax_type__iexact="VAT", then=F("items__tax_amount")),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            )
            + Sum(
                Case(
                    When(items__tax_type__iexact="TOT", then=F("items__tax_amount")),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            )
            + Sum(
                Case(
                    When(
                        ~Q(items__tax_type__iexact="VAT")
                        & ~Q(items__tax_type__iexact="TOT"),
                        then=F("items__tax_amount"),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            total_claimable_vat=Sum(
                Case(
                    When(
                        expired_vat=0,
                        then=F("items__tax_amount"),
                    ),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            total_expired_vat=Sum("expired_vat"),
        )

        return {
            "grouped": True,
            "group_by": group_by,
            "data": list(annotated),
        }
