# core/models/Documents.py

from django.db import models
from pathlib import Path
import hashlib
from datetime import date

from core.models.contact import Contact


import uuid
from pathlib import Path

# core/models/Documents.py
from pathlib import Path

def main_receipt_upload_path(instance, filename):
    """
    Generate: main_receipts/{receipt_number}_{recorded_by_tin}.ext
    Example: main_receipts/356_0921209714.pdf
    """
    ext = Path(filename).suffix.lower()
    receipt_number = instance.receipt_number or "unknown"
    recorded_by_tin = instance.company_tin or "unknown"
    return f"main_receipts/{receipt_number}_{recorded_by_tin}{ext}"


def withholding_receipt_upload_path(instance, filename):
    """
    Generate: withholding_receipts/{number}_{recorded_by_tin}.ext
    Example: withholding_receipts/WHT-001_0921209714.pdf
    """
    ext = Path(filename).suffix.lower()
    number = instance.withholding_receipt_number or "unknown"
    recorded_by_tin = instance.company_tin or "unknown"
    return f"withholding_receipts/{number}_{recorded_by_tin}{ext}"

class MainReceiptDocument(models.Model):
    receipt_number = models.CharField(max_length=100)
    
    company_tin = models.CharField(
        max_length=10,
        blank=False,
        null=False,
        help_text="10-digit TIN of the company receiving the receipt"
    )

    # File fields
    main_receipt = models.FileField(
        upload_to=main_receipt_upload_path,
        help_text="Main receipt PDF/document"
    )
    main_receipt_filename = models.CharField(max_length=255)
    main_receipt_content_type = models.CharField(max_length=100)
    main_receipt_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="MD5 hash to prevent re-upload of same file"
    )

    # Optional attachment
    attachment = models.FileField(
        upload_to=main_receipt_upload_path,
        null=True,
        blank=True,
        help_text="Optional additional attachment"
    )
    attachment_filename = models.CharField(max_length=255, null=True, blank=True)
    attachment_content_type = models.CharField(max_length=100, null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-compute file hash if not set
        if self.main_receipt and not self.main_receipt_hash:
            self.main_receipt.seek(0)
            file_data = self.main_receipt.read()
            self.main_receipt_hash = hashlib.md5(file_data).hexdigest()
            self.main_receipt.seek(0)  # Reset for saving
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Main Receipt: {self.receipt_number} ({self.company_tin})"

    class Meta:
        verbose_name = "Main Receipt Document"
        verbose_name_plural = "Main Receipt Documents"
        # ✅ CRITICAL: Add this constraint
        unique_together = [('receipt_number', 'company_tin')]


class WithholdingReceiptDocument(models.Model):
    withholding_receipt_number = models.CharField(
        max_length=100,
        help_text="Withholding receipt number from tax authority"
    )
    
    # Add company context (critical for uniqueness)
    company_tin = models.CharField(
        max_length=10,
        blank=False,
        null=False,
        help_text="10-digit TIN of the company receiving the withholding receipt"
    )

    withholding_receipt = models.FileField(
        upload_to=withholding_receipt_upload_path,
        help_text="Withholding tax receipt"
    )
    withholding_receipt_filename = models.CharField(max_length=255)
    withholding_receipt_content_type = models.CharField(max_length=100)

    withholding_attachment = models.FileField(
        upload_to=withholding_receipt_upload_path,
        null=True,
        blank=True,
        help_text="Optional attachment"
    )
    withholding_attachment_filename = models.CharField(max_length=255, null=True, blank=True)
    withholding_attachment_content_type = models.CharField(max_length=100, null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Withholding Receipt: {self.withholding_receipt_number} ({self.company_tin})"

    class Meta:
        verbose_name = "Withholding Receipt Document"
        verbose_name_plural = "Withholding Receipt Documents"
        # ✅ CRITICAL: Same company cannot have same withholding number
        unique_together = [('withholding_receipt_number', 'company_tin')]

class ReceiptDocument(models.Model):
    main_receipt = models.ForeignKey(
        MainReceiptDocument,
        on_delete=models.CASCADE,
        related_name="referenced_by",
    )
    withholding_receipt = models.ForeignKey(
        WithholdingReceiptDocument,
        on_delete=models.CASCADE,
        related_name="referenced_by",
        blank=True,
        null=True,
    )

    # Link to final Receipt (once created by clerk)
    linked_receipt = models.OneToOneField(
        'Receipt',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_document'
    )

    # Who uploaded it
    uploaded_by_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )

    # Company this is for
    for_company = models.ForeignKey(
        Contact,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='inbox_documents',
        help_text="The company this document is for"
    )

    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        default='uploaded',
        choices=[
            ('uploaded', 'Uploaded'),
            ('processed', 'Processed'),
            ('rejected', 'Rejected')
        ]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        wht = self.withholding_receipt.withholding_receipt_number if self.withholding_receipt else "None"
        return f"Doc: {self.main_receipt.receipt_number} + {wht}"


class Withholding(models.Model):
    withholding_receipt_number = models.CharField(max_length=50, unique=True)
    withholding_receipt_date = models.DateField()
    transaction_description = models.TextField(blank=True, null=True)

    sub_total = models.DecimalField(max_digits=20, decimal_places=2)
    tax_withholding_amount = models.DecimalField(max_digits=20, decimal_places=2)

    sales_invoice_number = models.CharField(max_length=50, blank=True, null=True)
    main_receipt_number = models.CharField(max_length=50, blank=True, null=True)

    buyer_tin = models.CharField(max_length=20, help_text="TIN of the buyer (deducting party)")
    seller_tin = models.CharField(max_length=20, help_text="TIN of the seller (service provider)")
    supplier_name = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"WHT {self.withholding_receipt_number} - ₵{self.tax_withholding_amount:,.2f}"

    class Meta:
        verbose_name = "Withholding Record"
        verbose_name_plural = "Withholding Records"
        ordering = ["-withholding_receipt_date"]