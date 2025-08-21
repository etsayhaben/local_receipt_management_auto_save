# core/serializers/ReceiptSerializer.py
from rest_framework import serializers
from decimal import Decimal
from core.models.item import Item
from core.models.contact import Contact
from core.models.PurchaseVoucher import PurchaseVoucher
from core.models.Documents import Withholding
from core.models.CRVITEM import CRVItem
from core.models.Receipt import ReceiptLine
from core.models.look_up_tables import ReceiptCatagory, ReceiptKind, ReceiptName, ReceiptType
from core.services.ReceiptService import ReceiptService
from core.services.RetrivingFromLookUpTables import RetrievingFromLookupTables
from core.services.UpdateReceipt import ReceiptUpdateService
# core/serializers/ReceiptSerializer.py
from rest_framework import serializers
from decimal import Decimal
from core.models.item import Item
from core.models.contact import Contact
from core.models.PurchaseVoucher import PurchaseVoucher
from core.models.Documents import Withholding
from core.models.CRVITEM import CRVItem
from core.models.Receipt import ReceiptLine
from core.models.Receipt import Receipt
from core.services.ReceiptService import ReceiptService
from core.services.RetrivingFromLookUpTables import RetrievingFromLookupTables

from rest_framework import serializers
from django.core.exceptions import ValidationError as DRFValidationError
from decimal import Decimal

# from core.services.receipt_validation import ReceiptValidationService  # Removed to avoid circular import

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["id", "name", "tin_number", "address"]

    def create(self, validated_data):
        tin_number = validated_data.get("tin_number")
        if tin_number:
            contact, _ = Contact.objects.get_or_create(
                tin_number=tin_number, defaults=validated_data
            )
            return contact
        return Contact.objects.create(**validated_data)


class CRVItemSerializer(serializers.ModelSerializer):
    # Rename 'amount_per_unit' to 'amount' for internal use
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        label="Amount per Unit",
        source="amount_per_unit",
    )

    class Meta:
        model = CRVItem
        fields = [
            "id",
            "receipt",
            "gl_account",
            "nature",
            "quantity",
            "amount",
            "total_amount",
            "reason_of_receiving",
            "item_description",
            "has_import_export",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "total_amount", "created_at", "updated_at"]
        extra_kwargs = {"receipt": {"required": False}}

    def validate(self, data):
        quantity = data.get("quantity", 1)
        amount_per_unit = data.get("amount_per_unit")
        if quantity <= 0:
            raise serializers.ValidationError({"quantity": "Must be > 0"})
        if not amount_per_unit or amount_per_unit <= 0:
            raise serializers.ValidationError({"amount_per_unit": "Must be > 0"})
        return data

    def create(self, validated_data):
        quantity = validated_data.get("quantity", 1)
        amount_per_unit = validated_data.get("amount_per_unit", 0)
        validated_data["total_amount"] = quantity * amount_per_unit
        return super().create(validated_data)

    def update(self, instance, validated_data):
        quantity = validated_data.get("quantity", instance.quantity)
        amount_per_unit = validated_data.get(
            "amount_per_unit", instance.amount_per_unit
        )
        validated_data["total_amount"] = quantity * amount_per_unit
        return super().update(instance, validated_data)


class ReceiptLineSerializer(serializers.Serializer):
    """
    Serializer for receipt line items.
    Accepts full item details inline — no need to pre-create Item.
    """

    item_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    item_description = serializers.CharField(max_length=200)
    unit_of_measurement = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    gl_account = serializers.CharField(max_length=50, required=False, allow_blank=True)
    nature = serializers.CharField(max_length=20, required=False, allow_blank=True)
    tax_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    unit_cost = serializers.DecimalField(decimal_places=2, max_digits=10)
    quantity = serializers.DecimalField(decimal_places=2, max_digits=10, default=1)
    discount_amount = serializers.DecimalField(
        decimal_places=2, max_digits=10, required=False, default=0
    )

    # ✅ Add these missing fields from the Item model
    hs_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    declaration_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    item_type = serializers.ChoiceField(
        choices=[("goods", "Goods"), ("service", "Service")],
        required=False,
        allow_null=True,
    )
    has_import_export = serializers.BooleanField(required=False, default=False)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

    def validate_unit_cost(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit cost cannot be negative.")
        return value

class ContactValidatorSerializer(serializers.Serializer):
    """Validates contact data without trying to create contacts"""
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    tin_number = serializers.CharField(max_length=10)
    address = serializers.CharField(required=False, allow_blank=True)

    def validate_tin_number(self, value):
        """Validate Ethiopian TIN format (10 digits)"""
        value = value.strip()
        if not value or len(value) != 10 or not value.isdigit():
            raise serializers.ValidationError("TIN must be exactly 10 digits (numbers only).")
        return value

class PurchaseVoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseVoucher
        fields = [
            "purchase_recipt_number",
            "supplier_name",
            "supplier_tin",
            "supplier_address",
            "date",
            "amount_paid",
            "description",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class WithholdingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withholding
        fields = [
            "withholding_receipt_number",
            "withholding_receipt_date",
            "transaction_description",
            "sub_total",
            "tax_withholding_amount",
            "sales_invoice_number",
            "buyer_tin",
            "seller_tin",
            "supplier_name",
        ]
        read_only_fields = [
            "created_at",
            "buyer_tin",
            "seller_tin",
            "supplier_name",
            "main_receipt_number",
            "tax_withholding_amount",
        ]




class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["id", "name", "tin_number", "address"]

    def create(self, validated_data):
        tin_number = validated_data.get("tin_number")
        if tin_number:
            contact, _ = Contact.objects.get_or_create(
                tin_number=tin_number, defaults=validated_data
            )
            return contact
        return Contact.objects.create(**validated_data)


class CRVItemSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        label="Amount per Unit",
        source="amount_per_unit",
    )

    class Meta:
        model = CRVItem
        fields = [
            "id",
            "receipt",
            "gl_account",
            "nature",
            "quantity",
            "amount",
            "total_amount",
            "reason_of_receiving",
            "transaction_description",
            "has_import_export",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "total_amount", "created_at", "updated_at"]
        extra_kwargs = {"receipt": {"required": False}}

    def validate(self, data):
        quantity = data.get("quantity", 1)
        amount_per_unit = data.get("amount_per_unit")
        if quantity <= 0:
            raise serializers.ValidationError({"quantity": "Must be > 0"})
        if not amount_per_unit or amount_per_unit <= 0:
            raise serializers.ValidationError({"amount_per_unit": "Must be > 0"})
        return data


class ReceiptLineSerializer(serializers.Serializer):
    item_code = serializers.CharField(max_length=50, required=False)
    item_description = serializers.CharField(max_length=200)
    unit_of_measurement = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    gl_account = serializers.CharField(max_length=50, required=False, allow_blank=True)
    nature = serializers.CharField(max_length=20, required=False, allow_blank=True)
    tax_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    unit_cost = serializers.DecimalField(decimal_places=2, max_digits=10)
    quantity = serializers.DecimalField(decimal_places=2, max_digits=10, default=1)

    discount_amount = serializers.DecimalField(
        decimal_places=2, max_digits=10, required=False, default=0
    )

    # ✅ Add missing fields
    item_type = serializers.CharField(
        max_length=50, required=False, allow_blank=True, allow_null=True
    )

    has_import_export = serializers.BooleanField(required=False, default=False)

    hs_code = serializers.CharField(
        max_length=50, required=False, allow_blank=True, allow_null=True
    )

    declaration_number = serializers.CharField(  # ✅ Correct spelling
        max_length=100, required=False, allow_blank=True, allow_null=True
    )

    # Optional: validate if needed
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

    def validate_unit_cost(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit cost cannot be negative.")
        return value


class PurchaseVoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseVoucher
        fields = [
            "purchase_recipt_number",
            "supplier_name",
            "supplier_tin",
            "supplier_address",
            "date",
            "amount_paid",
            "description",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class WithholdingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withholding
        fields = [
            "withholding_receipt_number",
            "withholding_receipt_date",
            "transaction_description",
            "sub_total",
            "tax_withholding_amount",
            "sales_invoice_number",
            "buyer_tin",
            "seller_tin",
            "supplier_name",
        ]
        read_only_fields = [
            "created_at",
            "buyer_tin",
            "seller_tin",
            "supplier_name",
            "main_receipt_number",
            "tax_withholding_amount",
        ]
# core/serializers/receipt_serializers.py

# core/serializers/receipt_serializers.py

from rest_framework import serializers
from django.core.exceptions import ValidationError

# Models
from core.models.Receipt import Receipt
from core.models.contact import Contact
from core.models.look_up_tables import ReceiptCatagory, ReceiptKind, ReceiptType, ReceiptName

# Nested serializers
from core.services.ReceiptService import ReceiptService


class ReceiptSerializer(serializers.Serializer):
    # ========================
    # NESTED SERIALIZERS
    # ========================
    issued_by_details = ContactValidatorSerializer()
    issued_to_details = ContactValidatorSerializer()
    withholding_details = WithholdingSerializer(required=False, allow_null=True)
    machine_number = serializers.CharField(allow_blank=True, required=False)

    # ========================
    # CORE FIELDS
    # ========================
    receipt_number = serializers.CharField(
        max_length=50,
        required=True,
        allow_blank=False
    )
    receipt_date = serializers.DateField()
    calendar_type = serializers.ChoiceField(
        choices=["gregorian", "ethiopian"],
        required=False,
        allow_null=True
    )

    # Classification IDs
    receipt_category_id = serializers.IntegerField()
    receipt_kind_id = serializers.IntegerField()
    receipt_type_id = serializers.IntegerField()
    receipt_name_id = serializers.IntegerField()

    is_withholding_applicable = serializers.BooleanField(default=False)
    payment_method_type = serializers.CharField(max_length=50)
    bank_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    # Line Items
    items = serializers.ListField(child=serializers.DictField())

    # Files (passed through to service)
    main_receipt_document = serializers.FileField(
        required=False,
        allow_null=True,
        read_only=False
    )
    attachement_receipt = serializers.FileField(
        required=False,
        allow_null=True,
        read_only=False
    )

    # ========================
    # READ-ONLY COMPUTED FIELDS
    # ========================
    subtotal = serializers.SerializerMethodField()
    tax = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    withholding_amount = serializers.SerializerMethodField()
    net_payable_to_supplier = serializers.SerializerMethodField()

    def get_subtotal(self, obj):
        return str(obj.subtotal)

    def get_tax(self, obj):
        return str(obj.tax)

    def get_total(self, obj):
        return str(obj.total)

    def get_withholding_amount(self, obj):
        return str(obj.withholding_amount)

    def get_net_payable_to_supplier(self, obj):
        return str(obj.net_payable_to_supplier)

    # ========================
    # VALIDATION
    # ========================
    def validate(self, attrs):
        recorded_by = self.context.get('recorded_by')
        if not recorded_by:
            raise serializers.ValidationError({
                "non_field_errors": ["Company context is missing. Please check your authentication."]
            })

        # Basic validation without ReceiptValidationService to avoid circular imports
        receipt_number = attrs.get("receipt_number", "").strip()
        if not receipt_number:
            raise serializers.ValidationError({"receipt_number": "This field is required."})

        # 🔒 Final business rule: Prevent duplicate receipt numbers
        if Receipt.objects.filter(
            receipt_number__iexact=receipt_number,
            recorded_by=recorded_by
        ).exists():
            raise serializers.ValidationError({
                "receipt_number": f"A receipt with number '{receipt_number}' for your company "
                                f"(TIN: {recorded_by.tin_number}) has already been created."
            })

        # ✅ Pass validated data back
        return attrs

    # ========================
    # CREATE
    # ========================
    def create(self, validated_data):
        # Extract nested contact data
        issued_by_data = validated_data.get("issued_by_details")
        issued_to_data = validated_data.get("issued_to_details")

        # ✅ GET recorded_by FROM CONTEXT
        recorded_by = self.context.get('recorded_by')
        if not recorded_by:
            raise serializers.ValidationError({
                "non_field_errors": ["Company context is missing. Cannot create receipt."]
            })

        # ✅ GET OR CREATE: issued_by
        if issued_by_data is not None:
            tin_number = issued_by_data["tin_number"].strip()
            try:
                issued_by = Contact.objects.get(tin_number=tin_number)
                # Update name and address
                issued_by.name = issued_by_data.get("name", "")
                issued_by.address = issued_by_data.get("address", "")
                issued_by.save()
            except Contact.DoesNotExist:
                issued_by = Contact.objects.create(
                    tin_number=tin_number,
                    name=issued_by_data.get("name", ""),
                    address=issued_by_data.get("address", "")
                )
        else:
            raise serializers.ValidationError({"issued_by_details": ["This field is required."]})

        # ✅ GET OR CREATE: issued_to
        if issued_to_data is not None:
            tin_number = issued_to_data["tin_number"].strip()
            try:
                issued_to = Contact.objects.get(tin_number=tin_number)
                issued_to.name = issued_to_data.get("name", "")
                issued_to.address = issued_to_data.get("address", "")
                issued_to.save()
            except Contact.DoesNotExist:
                issued_to = Contact.objects.create(
                    tin_number=tin_number,
                    name=issued_to_data.get("name", ""),
                    address=issued_to_data.get("address", "")
                )
        else:
            raise serializers.ValidationError({"issued_to_details": ["This field is required."]})

        # ✅ ADD resolved objects
        validated_data['issued_by'] = issued_by
        validated_data['issued_to'] = issued_to
        validated_data['recorded_by'] = recorded_by

        # ✅ CALL service (handles items, files, linking, etc.)
        receipt = ReceiptService.create_receipt(validated_data)

        return receipt

class ReceiptUpdateSerializer(serializers.Serializer):
    # Nested details (read-only or for display)
    issued_by_details = ContactSerializer(read_only=True)
    issued_to_details = ContactSerializer(read_only=True)

    # Basic fields - all optional for update
    receipt_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    receipt_date = serializers.DateField(required=False)
    calendar_type = serializers.ChoiceField(
        choices=["gregorian", "ethiopian"], required=False
    )

    # Foreign key IDs - optional, but validated if present
    receipt_category_id = serializers.IntegerField(required=False)
    receipt_kind_id = serializers.IntegerField(required=False)
    receipt_type_id = serializers.IntegerField(required=False)
    receipt_name_id = serializers.IntegerField(required=False)

    is_withholding_applicable = serializers.BooleanField(required=False)
    payment_method_type = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True)

    # Items - optional, but validated if provided
    items = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=True
    )

    withholding_details = WithholdingSerializer(required=False, allow_null=True)

    # Files

    # Computed (read-only) fields
    subtotal = serializers.SerializerMethodField()
    tax = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    withholding_amount = serializers.SerializerMethodField()
    net_payable_to_supplier = serializers.SerializerMethodField()

    def get_subtotal(self, obj):
        return str(obj.subtotal)

    def get_tax(self, obj):
        return str(obj.tax)

    def get_total(self, obj):
        return str(obj.total)

    def get_withholding_amount(self, obj):
        return str(obj.withholding_amount)

    def get_net_payable_to_supplier(self, obj):
        return str(obj.net_payable_to_supplier)

    def validate(self, attrs):
        """
        Validate only the fields being updated.
        If receipt_category_id is provided, validate it and validate items accordingly.
        """
        # Only validate if receipt_category_id is in the input
        if "receipt_category_id" in attrs:
            category_id = attrs["receipt_category_id"]
            category_name = RetrievingFromLookupTables.get_category_name_by_id(
                category_id
            )
            if not category_name:
                raise serializers.ValidationError(
                    {"receipt_category_id": "Invalid or unknown category ID."}
                )
            # Store category name for item validation
            attrs["_category_name"] = category_name.strip().lower()

        # Validate items only if provided
        if "items" in attrs and attrs["items"] is not None:
            category_name = attrs.get("_category_name")
            if not category_name:
                # Try to get from instance (existing object)
                if self.instance:
                    category_id = self.instance.receipt_category_id
                    name = RetrievingFromLookupTables.get_category_name_by_id(
                        category_id
                    )
                    category_name = name.strip().lower() if name else ""
                else:
                    raise serializers.ValidationError(
                        {"items": "Cannot validate items without a valid category."}
                    )

            item_serializer_class = (
                CRVItemSerializer if category_name == "crv" else ReceiptLineSerializer
            )
            validated_items = []
            for idx, item_data in enumerate(attrs["items"]):
                serializer = item_serializer_class(data=item_data)
                try:
                    serializer.is_valid(raise_exception=True)
                except Exception as e:
                    raise serializers.ValidationError(
                        {"items": [f"Item {idx + 1}: {str(e)}"]}
                    )
                validated_items.append(serializer.validated_data)
            attrs["items"] = validated_items

        return attrs

    def update(self, instance, validated_data):
        # Extract mutable fields
        update_fields = []

        # List of fields that can be updated
        updatable_fields = [
            "receipt_number",
            "receipt_date",
            "calendar_type",
            "receipt_category_id",
            "receipt_kind_id",
            "receipt_type_id",
            "receipt_name_id",
            "is_withholding_applicable",
            "payment_method_type",
            "bank_name",
        ]

        for field in updatable_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
                update_fields.append(field)

        # Handle items if provided
        if "items" in validated_data:
            # This assumes your service handles item replacement
            ReceiptService.update_receipt_items(instance, validated_data["items"])
            # No need to add to update_fields — handled separately

        # # Handle files
        # if "main_receipt_document" in validated_data:
        #     instance.main_receipt_document = validated_data["main_receipt_document"]
        #     update_fields.append("main_receipt_document")
        # if "attachement" in validated_data:
        #     instance.attachement = validated_data["attachement"]
        #     update_fields.append("attachement")

        # Save the receipt
        instance.save(update_fields=update_fields if update_fields else None)

        return instance

    def create(self, validated_data):
        raise NotImplementedError("Update serializer does not support create.")


# class UploadReceiptSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ReceiptDocument
#         fields = ['receipt_number', 'seller_tin_number', 'buyer_tin_number', 'MainReceipt', 'attachment']

#     def create(self, validated_data):
#         receipt_number = validated_data.get('receipt_number')

#         # Check for existing receipt with the same number
#         if ReceiptDocument.objects.filter(receipt_number=receipt_number).exists():
#             raise ValidationError({"receipt_number": "A receipt with this number already exists."})

#         return ReceiptDocument.objects.create(**validated_data)


# core/serializers.py


# Your models and nested serializers


class ReceiptUpdateSerializer(serializers.Serializer):
    # Nested read-only details
    issued_by_details = ContactSerializer()
    issued_to_details = ContactSerializer()

    # Updatable fields (all optional for PATCH)
    receipt_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    receipt_date = serializers.DateField(required=False)
    calendar_type = serializers.ChoiceField(
        choices=["gregorian", "ethiopian"], required=False
    )

    receipt_category_id = serializers.IntegerField(required=False)
    receipt_kind_id = serializers.IntegerField(required=False)
    receipt_type_id = serializers.IntegerField(required=False)
    receipt_name_id = serializers.IntegerField(required=False)

    is_withholding_applicable = serializers.BooleanField(required=False)
    payment_method_type = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True)

    items = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=True
    )
    withholding_details = WithholdingSerializer(required=False, allow_null=True)

    main_receipt_document = serializers.FileField(required=False, allow_null=True)
    attachement = serializers.FileField(
        required=False, allow_null=True
    )  # Typo? Should be "attachment"?

    # Computed fields (read-only)
    subtotal = serializers.SerializerMethodField()
    tax = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    withholding_amount = serializers.SerializerMethodField()
    net_payable_to_supplier = serializers.SerializerMethodField()

    def get_subtotal(self, obj):
        return str(obj.subtotal)

    def get_tax(self, obj):
        return str(obj.tax)

    def get_total(self, obj):
        return str(obj.total)

    def get_withholding_amount(self, obj):
        return str(obj.withholding_amount)

    def get_net_payable_to_supplier(self, obj):
        return str(obj.net_payable_to_supplier)

    def validate(self, attrs):
        # Validate category if provided
        if "receipt_category_id" in attrs:
            category_id = attrs["receipt_category_id"]
            category_name = RetrievingFromLookupTables.get_category_name_by_id(
                category_id
            )
            if not category_name:
                raise serializers.ValidationError(
                    {"receipt_category_id": "Invalid or unknown category ID."}
                )
            attrs["_category_name"] = category_name.strip().lower()

        # Validate items if provided
        if "items" in attrs and attrs["items"] is not None:
            category_name = attrs.get("_category_name")
            if not category_name and self.instance:
                cat_id = self.instance.receipt_category_id
                name = RetrievingFromLookupTables.get_category_name_by_id(cat_id)
                category_name = name.strip().lower() if name else None

            if not category_name:
                raise serializers.ValidationError(
                    {"items": "Cannot validate items without a valid category."}
                )

            ItemSerializerClass = (
                CRVItemSerializer if category_name == "crv" else ReceiptLineSerializer
            )
            validated_items = []
            for idx, item in enumerate(attrs["items"]):
                serializer = ItemSerializerClass(data=item)
                try:
                    serializer.is_valid(raise_exception=True)
                except Exception as e:
                    raise serializers.ValidationError(
                        {"items": [f"Item {idx + 1}: {str(e)}"]}
                    )
                validated_items.append(serializer.validated_data)
            attrs["items"] = validated_items

        return attrs

    def update(self, instance, validated_data):
        updatable_fields = [
            "receipt_number",
            "receipt_date",
            "calendar_type",
            "receipt_category_id",
            "receipt_kind_id",
            "receipt_type_id",
            "receipt_name_id",
            "is_withholding_applicable",
            "payment_method_type",
            "bank_name",
        ]

        # Update simple fields
        for field in updatable_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        # Update items if provided
        if "items" in validated_data:
            ReceiptUpdateService.update_receipt_items(instance, validated_data["items"])
        else:
            # Save if other fields changed
            instance.save()

        return instance

    def create(self, validated_data):
        raise NotImplementedError("Use create serializer for creation.")
