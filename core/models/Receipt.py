# core/models/models.py

from datetime import date
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

from core.models.Documents import Withholding
from core.models.contact import Contact
from core.models.item import Item
from core.models.look_up_tables import (
    ReceiptCatagory,
    ReceiptKind,
    ReceiptType,
    ReceiptName,
)
from core.models.PurchaseVoucher import PurchaseVoucher


# ========================
# Utility: VAT Expiration
# ========================
def is_date_expired(receipt_date: date) -> bool:
    today = date.today()
    first_day_of_prev_month = today.replace(day=1) - relativedelta(months=1)
    return receipt_date < first_day_of_prev_month


# ========================
# 1. Receipt Model
# ========================
class Receipt(models.Model):
    CALENDAR_CHOICES = [
        ("gregorian", "GC"),
        ("ethiopian", "EC"),
    ]

    # ========================
    # 0. Recording Context
    # ========================
    recorded_by = models.ForeignKey(
        Contact,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='recorded_receipts',
        help_text="The company entering this receipt (buyer for purchases, seller for sales)"
    )

    # ========================
    # 1. Core Parties
    # ========================
    issued_by = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name="sales",
        help_text="The entity issuing the receipt (always the seller/vendor)"
    )
    issued_to = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name="purchases",
        help_text="The entity receiving the receipt (always the buyer/customer)"
    )

    machine_number=models.CharField(max_length=50,blank=True,null=True)
    # ========================
    # 2. Document Identity
    # ========================
    receipt_number = models.CharField(
        max_length=50,
        help_text="Receipt/invoice number. Must be unique per vendor and date for your company."
    )
    receipt_date = models.DateField(help_text="Date of the transaction")
    calendar_type = models.CharField(
        max_length=11,
        choices=CALENDAR_CHOICES,
        blank=True,
        null=True,
        help_text="Gregorian or Ethiopian calendar"
    )

    # ========================
    # 3. Classification
    # ========================
    receipt_category = models.ForeignKey(
        ReceiptCatagory,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="receipts",
        help_text="High-level category (e.g., Taxable, Exempt)"
    )
    receipt_kind = models.ForeignKey(
        ReceiptKind,
        on_delete=models.PROTECT,
        related_name="receipts",
        help_text="Kind of receipt (e.g., Sales, Purchase)"
    )
    receipt_type = models.ForeignKey(
        ReceiptType,
        on_delete=models.PROTECT,
        related_name="receipts",
        help_text="Type (e.g., Invoice, Credit Note)"
    )
    receipt_name = models.ForeignKey(
        ReceiptName,
        on_delete=models.PROTECT,
        related_name="receipts",
        help_text="Specific name (e.g., VAT Invoice, Receipt)"
    )
    is_withholding_applicable = models.BooleanField(
        default=False,
        help_text="Indicates if withholding tax applies"
    )

    # ========================
    # 4. Payment Info
    # ========================
    payment_method_type = models.CharField(
        max_length=50,
        help_text="e.g., Cash, Bank Transfer, Mobile Money"
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name of bank if payment was via bank"
    )

    # ========================
    # 5. Documents
    # # ========================
    # main_receipt_document = models.FileField(
    #     upload_to="receipts/main/",
    #     help_text="Scanned official receipt or invoice"
    # )
    # attachement_receipt = models.FileField(
    #     upload_to="receipts/supporting/",
    #     blank=True,
    #     null=True,
    #     help_text="Optional: contract, delivery note, etc."
    # )

    # ========================
    # 6. Optional Links
    # ========================
    purchase_recipt_number = models.OneToOneField(
        PurchaseVoucher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_receipt",
        help_text="Link to purchase voucher if related"
    )
    withholding_receipt_number = models.ForeignKey(
        Withholding,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_receipts",
        help_text="Withholding document if tax was withheld"
    )
    reason_of_receiving = models.TextField(
        blank=True,
        null=True,
        help_text="Optional reason (e.g., service rendered, goods delivered)"
    )

    # ========================
    # 7. Metadata
    # ========================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ========================
    # 8. Financials & VAT Logic
    # ========================
    expired_vat = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="VAT lost due to late submission or expired claim period"
    )

    @property
    def subtotal(self):
        """Sum of all line item subtotals."""
        return sum(line.subtotal for line in self.items.all())

    @property
    def tax(self):
        """Sum of all line item tax amounts."""
        return sum(line.tax_amount for line in self.items.all())

    @property
    def total(self):
        """Total amount: subtotal + tax."""
        return self.subtotal + self.tax

    @property
    def is_vat_expired(self) -> bool:
        """Check if VAT is no longer claimable due to age."""
        return is_date_expired(self.receipt_date)

    @property
    def claimable_vat(self) -> Decimal:
        """VAT that can still be claimed."""
        return Decimal("0.00") if self.is_vat_expired else self.tax

    @property
    def non_claimable_vat(self) -> Decimal:
        """VAT that cannot be claimed (expired)."""
        return self.tax if self.is_vat_expired else Decimal("0.00")

    # ========================
    # 🔐 Validation
    # ========================
    def clean(self):
        super().clean()

        # Prevent exact duplicate: same company, vendor, number, and date
        if all([self.recorded_by, self.issued_by, self.receipt_number, self.receipt_date]):
            duplicate = Receipt.objects.exclude(pk=self.pk).filter(
                recorded_by=self.recorded_by,
                issued_by=self.issued_by,
                receipt_number=self.receipt_number,
                receipt_date=self.receipt_date
            )
            if duplicate.exists():
                raise ValidationError({
                    'receipt_number': (
                        f"A receipt with number '{self.receipt_number}' "
                        f"from {self.issued_by.name} on {self.receipt_date} "
                        "has already been recorded."
                    )
                })

    # ========================
    # 🏷️ String Representation
    # ========================
    def __str__(self):
        return f"📄 {self.receipt_number} | {self.issued_by.name} → {self.issued_to.name} | ₵{self.total:,.2f}"

    # ========================
    # 📚 Meta
    # ========================
    class Meta:
        ordering = ["-receipt_date"]
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"
        indexes = [
            models.Index(fields=["recorded_by", "receipt_date"]),
            models.Index(fields=["recorded_by", "issued_by", "receipt_number"]),
            models.Index(fields=["issued_by"]),
            models.Index(fields=["issued_to"]),
            models.Index(fields=["receipt_date"]),
            models.Index(fields=["receipt_number"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['recorded_by', 'issued_by', 'receipt_number', 'receipt_date'],
                name='unique_receipt_per_vendor_per_day'
            )
        ]

    def save(self, *args, **kwargs):
        # Auto-update expired_vat
        if self.is_vat_expired:
            self.expired_vat = self.tax
        else:
            self.expired_vat = Decimal("0.00")
        super().save(*args, **kwargs)


# ========================
# 2. Receipt Line Model
# ========================
class ReceiptLine(models.Model):
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, help_text="Catalog item")

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("1.00")
    )
    unit_cost = models.DecimalField(max_digits=20, decimal_places=2)
    tax_type = models.CharField(max_length=50)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2)
    discount_amount = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )

    @property
    def subtotal(self):
        return self.quantity * self.unit_cost - self.discount_amount

    @property
    def total_after_tax(self):
        return self.subtotal + self.tax_amount

    def save(self, *args, **kwargs):
        if not self.unit_cost:
            self.unit_cost = self.item.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} × {self.item.item_code} in {self.receipt.receipt_number}"

    class Meta:
        verbose_name = "Receipt Line"
        verbose_name_plural = "Receipt Lines"


# ========================
# 3. Thirty Percent Withholding
# ========================
class ThirtyPercentWithholdingReceipt(models.Model):
    supplier_name = models.CharField(max_length=255)
    withholding_receipt_number = models.CharField(max_length=100, unique=True)
    withholding_receipt_date = models.DateField()
    transaction_description = models.TextField(blank=True, null=True)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2)
    tax_withholding_amount = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False
    )
    buyer_tin = models.CharField(max_length=10)
    seller_tin = models.CharField(max_length=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        for field in ['buyer_tin', 'seller_tin']:
            value = getattr(self, field, None)
            if value and (not value.isdigit() or len(value.strip()) != 10):
                raise ValidationError({field: "Must be exactly 10 digits."})

    def save(self, *args, **kwargs):
        self.full_clean()
        self.tax_withholding_amount = (self.sub_total * Decimal("0.3")).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"WHT-{self.withholding_receipt_number} | {self.supplier_name}"

    class Meta:
        db_table = "thirty_percent_withholding_receipt"
        ordering = ["-withholding_receipt_date"]
        verbose_name = "30% Withholding Receipt"
        verbose_name_plural = "30% Withholding Receipts"