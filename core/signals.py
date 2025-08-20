from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps

from core.models.look_up_tables import ReceiptCatagory, ReceiptType
from .models.Receipt import ReceiptKind, ReceiptName
from django.db.models.signals import post_save
from core.models.Receipt import ReceiptKind
from core.models.Receipt import ReceiptName

# core/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from core.models.Receipt import ReceiptKind, ReceiptName


@receiver(post_migrate)
def create_default_receipt_data(sender, **kwargs):
    if sender.name == "core":
        # Receipt Categories
        for name in ["Revenue", "Expense", "CRV", "Other"]:
            ReceiptCatagory.objects.get_or_create(name=name.title())

        # Receipt Kinds
        for name in ["Manual", "Electronic", "Digital", "Other"]:
            ReceiptKind.objects.get_or_create(name=name.title())

        # Receipt Names
        for name in ["VAT", "TOT", "EXEMPTED", "ZERO", "MIXED"]:
            ReceiptName.objects.get_or_create(name=name.upper())
            # receipt type
       # for name in ["Cash", "Credit"]:
            #  ReceiptType.objects.get_or_create(name=name.upper())


def create_default_receipt_data(sender, **kwargs):
    print(f"post_migrate signal fired for app: {sender.name}")
    if sender.name == "core":
        print("Creating default receipt data...")
        # your code here
