# core/services/ReceiptService.py


from core import models


@staticmethod
def get_receipts_for_user(user_info: dict):
    """
    Return all receipts where the user's company is either:
      - The issuer (issued_by)
      - The receiver (issued_to)
    """
    from core.models.Receipt import Receipt

    user_tin = user_info.get("tin")
    if not user_tin:
        raise ValueError("User TIN is required to filter receipts")

    # Log for debugging
    print(f"📄 Fetching receipts for company TIN: {user_tin}")
    receipts = (
        Receipt.objects.select_related("issued_by", "issued_to")
        .filter(
            models.Q(issued_by__tin_number=user_tin)
            | models.Q(issued_to__tin_number=user_tin)
        )
        .order_by("-receipt_date")
    )

    return receipts
