# models/PurchaseVoucher.py
from django.db import models


class PurchaseVoucher(models.Model):
    supplier_name = models.CharField(max_length=255)
    supplier_tin = models.CharField(max_length=50, blank=True, null=True)
    supplier_address = models.TextField()
    date = models.DateField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    purchase_recipt_number = models.CharField(max_length=100)

    # Binary fields to store file contents
    document = models.BinaryField(blank=True, null=True)  # Store file as bytes
    document_filename = models.CharField(
        max_length=255, blank=True, null=True
    )  # To preserve filename
    document_content_type = models.CharField(max_length=100, blank=True, null=True)

    attachment = models.BinaryField(blank=True, null=True)
    attachment_filename = models.CharField(max_length=255, blank=True, null=True)
    attachment_content_type = models.CharField(max_length=100, blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)  # Set once on creation
    updated_at = models.DateTimeField(auto_now=True)  # Updated on every save

    def __str__(self):
        return self.purchase_recipt_number

    class Meta:
        # Optional: Add ordering (e.g., newest first)
        ordering = ["-created_at"]
