from django.db import models


# models.py
from django.db import models
from decimal import Decimal


class Item(models.Model):
    CATEGORY_CHOICES = (
        ("goods", "Goods"),
        ("service", "Service"),
    )

    gl_account = models.CharField(
        max_length=10, help_text="General Ledger account code"
    )
    nature = models.CharField(
        max_length=50, null=True, blank=True, help_text="e.g., Consumable, Asset"
    )
    hs_code = models.CharField(
        max_length=20, blank=True, null=True, help_text="HS Code for customs"
    )
    item_code = models.CharField(
        max_length=20, unique=True, help_text="SKU or internal code"
    )
    item_type = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, null=True, blank=True
    )
    tax_type = models.CharField(max_length=50, help_text="e.g., VAT 15%, Exempt")
    has_import_export = models.BooleanField(default=False)
    declaration_number = models.CharField(max_length=50, blank=True, null=True)
    item_description = models.TextField()
    unit_of_measurement = models.CharField(max_length=50, null=True, blank=True)

    # Default unit cost (can be overridden per receipt)
    unit_cost = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )

    def __str__(self):
        return f"{self.item_code}: {self.item_description}"

    class Meta:
        verbose_name = "Item"
        verbose_name_plural = "Items"
