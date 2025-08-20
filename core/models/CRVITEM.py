# core/models/crv.py

from django.db import models
from core.models.Receipt import Receipt
from decimal import Decimal


class CRVItem(models.Model):
    """
    Line item for Cash Receipt Voucher (CRV).
    Represents income received (e.g., customer payment, donation, service income).
    Linked directly to a Receipt for simplicity.
    """

    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name="crv_items",  # e.g., receipt.crv_items.all()
        help_text="The receipt this CRV item belongs to",
    )

    # General Ledger & Classification
    gl_account = models.CharField(
        max_length=100,
        help_text="General Ledger account code (e.g., 4100 for Sales Income)",
    )
    nature = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nature of income: e.g., Donation, Service Income, Grant",
    )

    # Quantity and Unit Amount (for services or goods sold)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        help_text="Number of units (e.g., hours, items)",
    )
    amount_per_unit = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Income per unit before tax/discount",
    )

    # Calculated Fields
    @property
    def subtotal(self):
        """Total before tax or deductions"""
        return self.quantity * self.amount_per_unit

    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Net amount received after tax/deductions (if any)",
    )

    declaration_number = models.CharField(max_length=50, blank=True, null=True)

    # Description of income
    reason_of_receiving = models.TextField(
        help_text="Detailed reason for receiving money (e.g., 'Payment for May consulting services')",
    )

    # Optional: Track if this is from an imported service (rare, but possible)
    has_import_export = models.BooleanField(  # Fixed: was CharField!
        default=False,
        help_text="Check if this income relates to imported service (e.g., foreign client)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CRV: {self.total_amount:,.2f} | {self.transaction_description or 'Income'}"

    class Meta:
        verbose_name = "CRV Item"
        verbose_name_plural = "CRV Items"
        ordering = ["-created_at"]
