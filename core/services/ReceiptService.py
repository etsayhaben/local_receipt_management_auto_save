import jwt
import base64
import traceback
import io
from django.conf import settings
from django.db import transaction
from django.db.models import F
from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
# Models
from core.models.Receipt import Receipt, ReceiptLine
from core.models.contact import Contact
from core.models.PurchaseVoucher import PurchaseVoucher
from core.models.Documents import MainReceiptDocument, ReceiptDocument, Withholding
from core.models.CRVITEM import CRVItem
from core.models.item import Item

# Services
from core.services.RetrivingFromLookUpTables import RetrievingFromLookupTables


class ReceiptService:
    # 🔑 Hardcoded to match Spring Boot's key
    SPRING_BOOT_KEY = "413f4428472B4B6250655368566D970337336763979244226452948404D6351"

    @staticmethod
    def _get_secret_bytes() -> bytes:
        """
        Replicate Spring Boot's behavior:
        Treat a hex-like string as if it were Base64-encoded.
        """
        key = "413f4428472B4B6250655368566D970337336763979244226452948404D63510"
        padded_key = key
        while len(padded_key) % 4 != 0:
            padded_key += "="
        try:
            secret_bytes = base64.b64decode(padded_key, validate=False)
            return secret_bytes
        except Exception as e:
            raise ValueError(f"Failed to decode JWT key: {str(e)}")

    @staticmethod
    def decode_jwt(token: str) -> dict:
        """
        Decode JWT token from Spring Boot.
        """
        print("🔴 Token type:", type(token))
        print("🔴 Token length:", len(token) if token else 0)
        print("🔴 Token first 50 chars:", token[:50])
        print("🔴 Token last 50 chars:", token[-50:])
        print("🔴 Raw token received:", repr(token))
        segments = token.split(".") if token else []
        print("🔴 Number of segments:", len(segments))
        print("🔴 Has 'Bearer' in it?", "bearer" in token.lower() if token else "no")
     
        try:
            secret_bytes = ReceiptService._get_secret_bytes()
            payload = jwt.decode(token, secret_bytes, algorithms=["HS256"])
            if "tin_number" not in payload:
                raise serializers.ValidationError("Token missing 'tin_number'")
            if "user_id" not in payload:
                raise serializers.ValidationError("Token missing 'user_id'")
            return payload
        except jwt.ExpiredSignatureError:
            raise serializers.ValidationError("Token has expired")
        except jwt.InvalidTokenError as e:
            if settings.DEBUG:
                with io.StringIO() as buf:
                    traceback.print_exc(file=buf)
                    detailed_traceback = buf.getvalue()
                error_msg = f"Invalid or malformed token: {str(e)}\nTraceback:\n{detailed_traceback}"
            else:
                error_msg = "Invalid or malformed token"
            raise serializers.ValidationError(error_msg)

    @staticmethod
    def get_user_info_from_payload(payload: dict) -> dict:
        first_name = payload.get("first_name", "Unknown")
        last_name = payload.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        return {
            "tin": payload["tin_number"],
            "name": full_name,
            "first_name": first_name,
            "user_id": payload["user_id"],
            "email": payload.get("email", ""),
            "company_name": payload.get("company_name", ""),
            "roles": payload.get("roles", []),
            "is_clerk": "CLERK" in payload.get("roles", []),
            "is_admin": "ADMIN" in payload.get("roles", [])
            or "SUPERUSER" in payload.get("roles", []),
        }

    @staticmethod
    def get_user_info_from_request(request) -> dict:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise serializers.ValidationError("Authorization header missing or invalid")
        token = auth_header.split(" ")[1]
        payload = ReceiptService.decode_jwt(token)
        return ReceiptService.get_user_info_from_payload(payload)

    @staticmethod
    def calculate_totals(receipt_data: dict) -> dict:
        subtotal = Decimal("0.0000")
        total_tax = Decimal("0.0000")
        items = receipt_data.get("items", [])

        for item in items:
            unit_cost = Decimal(str(item.get("unit_cost", 0)))
            quantity = Decimal(str(item.get("quantity", 1)))
            item_type = str(item.get("item_type", "")).lower()
            tax_type = str(item.get("tax_type", "")).upper()

            line_total = unit_cost * quantity
            subtotal += line_total

            if tax_type == "VAT":
                tax_rate = Decimal("15.0")
            elif tax_type == "TOT":
                if item_type == "goods":
                    tax_rate = Decimal("2.0")
                elif item_type == "services":
                    tax_rate = Decimal("10.0")
                else:
                    tax_rate = Decimal("0.0")
            else:
                tax_rate = Decimal("0.0")

            item_tax = (line_total * tax_rate / 100).quantize(
                Decimal("0.0000"), rounding=ROUND_HALF_UP
            )
            total_tax += item_tax

        total = subtotal + total_tax

        withholding_amount = Decimal("0.0000")
        if receipt_data.get("is_withholding_applicable", False):
            if item_type == "goods" and subtotal >= Decimal("20000"):
                withholding_amount = (subtotal * Decimal("0.03")).quantize(
                    Decimal("0.0000"), rounding=ROUND_HALF_UP
                )
            elif item_type == "service" and subtotal >= Decimal("30000"):
                withholding_amount = (subtotal * Decimal("0.03")).quantize(
                    Decimal("0.0000"), rounding=ROUND_HALF_UP
                )
        else:
            withholding_amount = Decimal("0.0000")

        net_payable_to_supplier = total - withholding_amount

        return {
            "subtotal": subtotal,
            "tax": total_tax,
            "withholding_amount": withholding_amount,
            "total": total,
            "net_payable_to_supplier": net_payable_to_supplier,
        }

    @staticmethod
    @transaction.atomic
    def create_receipt(validated_data: dict) -> Receipt:
        """
        Full business logic: Create receipt from validated data.
        Assumes:
        - Files were uploaded first → ReceiptDocument exists with status='uploaded'
        - This receipt is being created based on that uploaded document
        - Link back to ReceiptDocument so get_documents() works
        """
        # === STEP 1: Extract and clean data ===
        issued_by = validated_data.pop("issued_by", None)
        issued_to = validated_data.pop("issued_to", None)

        # Remove nested details (already used)
        validated_data.pop("issued_by_details", None)
        validated_data.pop("issued_to_details", None)

        # Extract items and optional data
        items_data = validated_data.pop("items", [])
        pv_data = validated_data.pop("purchase_voucher_details", None)
        wh_data = validated_data.pop("withholding_details", None)

        # Remove computed fields
        for field in [
            "subtotal", "tax", "total",
            "withholding_amount", "net_payable_to_supplier",
            "has_import_export", "hs_code", "item_code",
            "declaration_number", "item_type",
        ]:
            validated_data.pop(field, None)

        # Ensure recorded_by is present
        recorded_by = validated_data.get("recorded_by")
        if not recorded_by:
            raise ValidationError({"recorded_by": "This field is required."})

        # Get receipt_number early (needed to find uploaded document)
        receipt_number = validated_data.get("receipt_number")
        if not receipt_number:
            raise ValidationError({"receipt_number": "This field is required to link to uploaded document."})

        # === STEP 2: Create Receipt instance ===
        receipt = Receipt(
            issued_by=issued_by,
            issued_to=issued_to,
            **validated_data
        )

        # Enforce model-level validation
        receipt.full_clean()

        # Save to get primary key
        receipt.save(force_insert=True)
        receipt = Receipt.objects.get(id=receipt.id)  # Re-fetch to avoid state issues

        if not receipt.pk:
            raise ValidationError("Failed to create receipt: missing primary key.")

        # === STEP 3: Create line items ===
        if items_data:
            category_id = validated_data.get("receipt_category_id")
            category_name = RetrievingFromLookupTables.get_category_name_by_id(category_id)
            is_crv = category_name and category_name.strip().lower() == "crv"

            if is_crv:
                for item_data in items_data:
                    CRVItem.objects.create(receipt=receipt, **item_data)
            else:
                for index, item_data in enumerate(items_data):
                    item_code = item_data.get("item_code", f"TEMP-{receipt.id}-{index}")
                    item_description = item_data["item_description"]
                    unit_of_measurement = item_data.get("unit_of_measurement", "unit")
                    gl_account = item_data.get("gl_account", "4000")
                    nature = item_data.get("nature", "goods")
                    tax_type = item_data.get("tax_type", "")
                    unit_cost = Decimal(str(item_data["unit_cost"]))

                    # Optional fields
                    hs_code = item_data.get("hs_code", "")
                    has_import_export = item_data.get("has_import_export", False)
                    declaration_number = item_data.get("declaration_number", "")
                    item_type = item_data.get("item_type", "goods")

                    # Get or create Item
                    item, created = Item.objects.get_or_create(
                        item_code=item_code,
                        defaults={
                            "item_description": item_description,
                            "unit_of_measurement": unit_of_measurement,
                            "gl_account": gl_account,
                            "nature": nature,
                            "tax_type": tax_type,
                            "unit_cost": unit_cost,
                            "hs_code": hs_code,
                            "has_import_export": has_import_export,
                            "declaration_number": declaration_number,
                            "item_type": item_type,
                        },
                    )

                    if not created:
                        item.item_description = item_description
                        item.unit_of_measurement = unit_of_measurement
                        item.gl_account = gl_account
                        item.nature = nature
                        item.tax_type = tax_type
                        item.unit_cost = unit_cost
                        item.hs_code = hs_code
                        item.has_import_export = has_import_export
                        item.declaration_number = declaration_number
                        item.item_type = item_type
                        item.save()

                    # Calculate totals
                    quantity = Decimal(str(item_data.get("quantity", 1)))
                    discount_amount = Decimal(str(item_data.get("discount_amount", "0.00")))
                    raw_total = unit_cost * quantity - discount_amount

                    # Tax calculation
                    if tax_type == "VAT":
                        tax_rate = Decimal("15.0")
                    elif tax_type == "EXEMPTED":
                        tax_rate = Decimal("0.0")
                    elif tax_type == "TOT":
                        tax_rate = Decimal("2.0") if item_type == "goods" else Decimal("10.0")
                    else:
                        tax_rate = Decimal("0.0")

                    tax_amount = (raw_total * tax_rate / 100).quantize(
                        Decimal("0.00"), rounding=ROUND_HALF_UP
                    )

                    # Create ReceiptLine
                    ReceiptLine.objects.create(
                        receipt=receipt,
                        item=item,
                        quantity=quantity,
                        unit_cost=unit_cost,
                        tax_type=tax_type,
                        tax_amount=tax_amount,
                        discount_amount=discount_amount,
                    )
        else:
            print("No items provided for receipt creation")

        # === STEP 4: LINK TO EXISTING ReceiptDocument — MATCH (PREFIX+NUMBER) OR (NUMBER ONLY) ===
        import re

        system_number = receipt.receipt_number.strip()

        # Try to split into prefix and digits (e.g., FS246 → "FS", "246")
        match = re.match(r"^([A-Za-z]+)(\d+)$", system_number)
        if match:
            prefix, doc_digits = match.groups()
            candidates = [
                system_number,           # FS246
                system_number.upper(),   # FS246
                system_number.lower(),   # fs246
                doc_digits,              # 246
            ]
        else:
            # No prefix+number pattern → just use as-is
            candidates = [system_number]

        receipt_document = None

        try:
            for candidate in candidates:
                try:
                    # First: try exact match
                    main_docs = MainReceiptDocument.objects.filter(receipt_number=candidate)
                    if not main_docs.exists():
                        # Fallback: case-insensitive
                        main_docs = MainReceiptDocument.objects.filter(receipt_number__iexact=candidate)

                    for main_doc in main_docs:
                        try:
                            rd = ReceiptDocument.objects.get(
                                main_receipt=main_doc,
                                for_company=recorded_by,
                                linked_receipt__isnull=True,
                                status='uploaded'
                            )
                            receipt_document = rd
                            break
                        except ReceiptDocument.DoesNotExist:
                            continue
                    if receipt_document:
                        break
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Error matching candidate '{candidate}': {e}")
                    continue

            # 🔗 If found, link back
            if receipt_document:
                receipt_document.linked_receipt = receipt
                receipt_document.status = 'processed'
                receipt_document.save()
                print(f"✅ Linked uploaded doc '{receipt_document.main_receipt.receipt_number}' → '{system_number}'")
            else:
                print(f"❌ No uploaded document found for: {system_number} (tried: {candidates})")

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Unexpected error linking document for receipt {system_number}")

        # === STEP 5: Handle Purchase Voucher (optional) ===
        if pv_data:
            purchase_voucher = PurchaseVoucher.objects.create(**pv_data)
            receipt.purchase_receipt_number = purchase_voucher
            receipt.save()

        # === STEP 6: Auto-generate Withholding (if applicable) ===
        if not wh_data and validated_data.get("is_withholding_applicable"):
            sub_total = receipt.subtotal
            withholding_rate = Decimal("0.02")
            tax_withholding_amount = (sub_total * withholding_rate).quantize(
                Decimal("0.00"), rounding=ROUND_HALF_UP
            )
            wh_data = {
                "withholding_receipt_number": f"WHT-{receipt.id:06d}",
                "withholding_receipt_date": receipt.receipt_date,
                "transaction_description": "Auto-generated withholding",
                "sub_total": sub_total,
                "tax_withholding_amount": tax_withholding_amount,
                "buyer_tin": issued_by.tin_number,
                "seller_tin": issued_to.tin_number,
                "supplier_name": issued_to.name,
            }

        if wh_data:
            if not wh_data.get("tax_withholding_amount"):
                sub_total = Decimal(str(wh_data.get("sub_total", 0)))
                wh_data["tax_withholding_amount"] = (sub_total * Decimal("0.02")).quantize(
                    Decimal("0.00"), rounding=ROUND_HALF_UP
                )
            withholding = Withholding.objects.create(**wh_data)
            receipt.withholding_receipt_number = withholding
            receipt.save()

        return receipt
