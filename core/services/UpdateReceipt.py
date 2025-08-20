# core/services/UpdateService.py

from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404

from core.models.Receipt import ReceiptLine
from core.models.item import Item


class ReceiptUpdateService:
    @staticmethod
    @transaction.atomic
    def update_receipt_items(receipt, items_data):
        # Delete existing items
        receipt.items.all().delete()

        # Reset totals
        subtotal = Decimal("0.00")
        tax = Decimal("0.00")
        claimable_vat = Decimal("0.00")
        expired_vat = Decimal("0.00")

        for item_data in items_data:
            # Extract item_id from payload
            item_id = item_data.get("item")
            if not item_id:
                raise ValueError("Each item must include 'item' (ID of the Item).")

            item = get_object_or_404(Item, id=item_id)

            # Use Decimal safely
            quantity = Decimal(str(item_data.get("quantity", 1)))
            unit_cost = Decimal(str(item_data.get("unit_cost", item.unit_cost)))
            discount_amount = Decimal(str(item_data.get("discount_amount", 0)))
            tax_amount = Decimal(str(item_data.get("tax_amount", 0)))

            line_subtotal = (quantity * unit_cost) - discount_amount
            subtotal += line_subtotal
            tax += tax_amount

            is_vat_expired = item_data.get("is_vat_expired", False)
            if is_vat_expired:
                expired_vat += tax_amount
            else:
                claimable_vat += tax_amount

            # Create ReceiptLine with only valid fields
            ReceiptLine.objects.create(
                receipt=receipt,
                item=item,
                quantity=quantity,
                unit_cost=unit_cost,
                tax_type=item.tax_type,  # or override from payload
                tax_amount=tax_amount,
                discount_amount=discount_amount,
            )

        # Update receipt totals
        receipt.subtotal = subtotal
        receipt.tax = tax
        receipt.total = subtotal + tax
        receipt.claimable_vat = claimable_vat
        receipt.non_claimable_vat = Decimal("0.00")
        receipt.expired_vat = expired_vat
        receipt.is_vat_expired = expired_vat > Decimal("0.00")

        receipt.save()
        return receipt
