# core/serializers/DocumentSerializer.py

import os
import hashlib
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
import logging
from django.core.files.storage import default_storage
logger = logging.getLogger(__name__)

# Models
from core.models.Documents import (
    ReceiptDocument,
    MainReceiptDocument,
    WithholdingReceiptDocument
)
from core.models.contact import Contact


class DocumentListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    document_type = serializers.CharField()  # "main" or "withholding"
    receipt_number = serializers.CharField()
    company_tin = serializers.CharField()
    uploaded_at = serializers.DateTimeField()
    file_url = serializers.SerializerMethodField()
    status = serializers.CharField()
    has_attachment = serializers.BooleanField()
    main_document_id = serializers.IntegerField(allow_null=True)
    withholding_document_id = serializers.IntegerField(allow_null=True)

    def get_file_url(self, obj):
        if obj['document_type'] == "main":
            return obj['main_receipt_url']
        else:
            return obj['withholding_receipt_url']


class MainReceiptDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainReceiptDocument
        fields = [
            "receipt_number",
            "company_tin",
            "main_receipt",
            "attachment",
        ]
        read_only_fields = ["company_tin"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
            field.allow_null = True
            if hasattr(field, "allow_empty_file"):
                field.allow_empty_file = True

    def create(self, validated_data):
        for_company = self.context.get("for_company")
        if not for_company:
            raise DRFValidationError({"company_tin": "Company context missing."})
        validated_data["company_tin"] = for_company.tin_number
        return super().create(validated_data)


class WithholdingReceiptDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithholdingReceiptDocument
        fields = [
            "withholding_receipt_number",
            "company_tin",
            "withholding_receipt",
            "withholding_attachment",
        ]
        read_only_fields = ["company_tin"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
            field.allow_null = True
            if hasattr(field, "allow_empty_file"):
                field.allow_empty_file = True

    def create(self, validated_data):
        for_company = self.context.get("for_company")
        if not for_company:
            raise DRFValidationError({"company_tin": "Company context missing."})
        validated_data["company_tin"] = for_company.tin_number
        return super().create(validated_data)


class UploadReceiptSerializer(serializers.ModelSerializer):
    main_receipt_data = MainReceiptDocumentSerializer(write_only=True, required=False)
    withholding_receipt_data = WithholdingReceiptDocumentSerializer(write_only=True, required=False)
    main_receipt = serializers.PrimaryKeyRelatedField(
        queryset=MainReceiptDocument.objects.all(),
        required=False,
        allow_null=True,
    )
    withholding_receipt = serializers.PrimaryKeyRelatedField(
        queryset=WithholdingReceiptDocument.objects.all(),
        required=False,
        allow_null=True,
    )
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ReceiptDocument
        fields = [
            "main_receipt",
            "main_receipt_data",
            "withholding_receipt",
            "withholding_receipt_data",
            "notes",
        ]

    def validate(self, data):
        request = self.context.get("request")
        if not request or not request.FILES:
            raise DRFValidationError("No file uploaded.")

        has_main_by_id = "main_receipt" in data
        has_main_by_data = "main_receipt_data" in data

        if not has_main_by_id and not has_main_by_data:
            raise DRFValidationError({
                "main_receipt": "Either 'main_receipt' (ID) or 'main_receipt_data' (upload) must be provided."
            })

        main_data = data.get("main_receipt_data")
        if not main_data:
            return data

        receipt_number = main_data.get("receipt_number")
        for_company = self.context.get("for_company")
        if not for_company:
            raise DRFValidationError({"company_tin": "Company context is missing."})

        company_tin = for_company.tin_number

        if not receipt_number:
            raise DRFValidationError({"main_receipt_data": "Receipt number is required."})

        main_data["company_tin"] = company_tin

        # Prevent duplicate receipt number for same company
        if MainReceiptDocument.objects.filter(
            receipt_number__iexact=receipt_number,
            company_tin__iexact=company_tin
        ).exists():
            raise DRFValidationError({
                "receipt_number": f"A receipt with number '{receipt_number}' for your company "
                                f"(TIN: {company_tin}) has already been uploaded."
            })

        # Prevent duplicate file content
        main_file_key = "main_receipt_data.main_receipt"
        if main_file_key in request.FILES:
            uploaded_file = request.FILES[main_file_key]
            file_content = uploaded_file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            uploaded_file.seek(0)

            if MainReceiptDocument.objects.filter(main_receipt_hash=file_hash).exists():
                raise DRFValidationError({"file": "This exact file has already been uploaded."})

            main_data["main_receipt_hash"] = file_hash

        withholding_data = data.get("withholding_receipt_data")
        if withholding_data:
            withholding_number = withholding_data.get("withholding_receipt_number")
            if withholding_number:
                if WithholdingReceiptDocument.objects.filter(
                    withholding_receipt_number__iexact=withholding_number,
                    company_tin__iexact=company_tin
                ).exists():
                    raise DRFValidationError({
                        "withholding_receipt_number": f"A withholding receipt with number '{withholding_number}' "
                                                   f"for your company (TIN: {company_tin}) has already been uploaded."
                    })

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        for_company = self.context.get("for_company")
         
        if not for_company:
            raise DRFValidationError("Missing company context.")

        uploaded_by = Contact.objects.get_or_create(
            tin_number=for_company.tin_number,
            
            defaults={
                "name": "New Company",
                "address": "Address not provided"
            }
        )[0]

        notes = validated_data.pop("notes", "")
        main_data = validated_data.pop("main_receipt_data", None)
        withholding_data = validated_data.pop("withholding_receipt_data", None)

        main_receipt = None
        if main_data:
            main_file_key = "main_receipt_data.main_receipt"
            if main_file_key not in request.FILES:
                raise DRFValidationError({"main_receipt_data": f"File '{main_file_key}' is required."})

            main_file = request.FILES[main_file_key]

            # Set metadata
            main_data.setdefault("main_receipt_filename", get_valid_filename(main_file.name))
            main_data.setdefault("main_receipt_content_type", main_file.content_type or "application/octet-stream")

            attach_key = "main_receipt_data.attachment"
            if attach_key in request.FILES:
                attach_file = request.FILES[attach_key]
                main_data.setdefault("attachment_filename", get_valid_filename(attach_file.name))
                main_data.setdefault("attachment_content_type", attach_file.content_type or "application/octet-stream")

            main_data["company_tin"] = for_company.tin_number

            # Create instance (without saving file yet)
            main_receipt = MainReceiptDocument(**main_data)
            main_receipt.save()  # Triggers upload_to path generation

            # Save main receipt file
            ext = os.path.splitext(main_file.name)[1]
            filename = f"{main_data['receipt_number']}_{for_company.tin_number}{ext}"
            try:
                main_file.seek(0)
                main_receipt.main_receipt.save(
                    name=filename,
                    content=ContentFile(main_file.read()),
                    save=True
                )
                logger.info(f"Main receipt saved: {main_receipt.main_receipt.path}")
            except Exception as e:
                main_receipt.delete()
                logger.error(f"Failed to save main receipt: {str(e)}", exc_info=True)
                raise DRFValidationError({"file": f"Failed to save main receipt: {str(e)}"})

            # Save attachment
            if attach_key in request.FILES:
                attach_file = request.FILES[attach_key]
                attach_ext = os.path.splitext(attach_file.name)[1]
                attach_filename = f"{main_data['receipt_number']}_{for_company.tin_number}_attachment{attach_ext}"
                try:
                    attach_file.seek(0)
                    main_receipt.attachment.save(
                        name=attach_filename,
                        content=ContentFile(attach_file.read()),
                        save=True
                    )
                    logger.info(f"Attachment saved: {main_receipt.attachment.path}")
                except Exception as e:
                    main_receipt.delete()
                    logger.error(f"Failed to save attachment: {str(e)}", exc_info=True)
                    raise DRFValidationError({"attachment": f"Failed to save attachment: {str(e)}"})

        else:
            main_receipt = validated_data.get("main_receipt")

        if not main_receipt:
            raise DRFValidationError("Main receipt is required.")

        # === Withholding Receipt ===
        withholding_receipt = None
        if withholding_data is not None:
            wht_file_key = "withholding_receipt_data.withholding_receipt"
            if wht_file_key in request.FILES:
                wht_file = request.FILES[wht_file_key]

                withholding_data.setdefault("withholding_receipt_filename", get_valid_filename(wht_file.name))
                withholding_data.setdefault("withholding_receipt_content_type", wht_file.content_type or "application/octet-stream")

                wht_attach_key = "withholding_receipt_data.withholding_attachment"
                if wht_attach_key in request.FILES:
                    attach_file = request.FILES[wht_attach_key]
                    withholding_data.setdefault("withholding_attachment_filename", get_valid_filename(attach_file.name))
                    withholding_data.setdefault("withholding_attachment_content_type", attach_file.content_type or "application/octet-stream")

                if "withholding_receipt_number" not in withholding_data:
                    raise DRFValidationError({
                        "withholding_receipt_data": "Field 'withholding_receipt_number' is required."
                    })

                withholding_data["company_tin"] = for_company.tin_number

                withholding_receipt = WithholdingReceiptDocument(**withholding_data)
                withholding_receipt.save()

                # Save withholding receipt
                ext = os.path.splitext(wht_file.name)[1]
                filename = f"{withholding_data['withholding_receipt_number']}_{for_company.tin_number}{ext}"
                try:
                    wht_file.seek(0)
                    withholding_receipt.withholding_receipt.save(
                        name=filename,
                        content=ContentFile(wht_file.read()),
                        save=True
                    )
                    logger.info(f"Withholding receipt saved: {withholding_receipt.withholding_receipt.path}")
                except Exception as e:
                    withholding_receipt.delete()
                    logger.error(f"Failed to save withholding receipt: {str(e)}", exc_info=True)
                    raise DRFValidationError({"file": f"Failed to save withholding receipt: {str(e)}"})

                # Save attachment
                if wht_attach_key in request.FILES:
                    attach_file = request.FILES[wht_attach_key]
                    attach_ext = os.path.splitext(attach_file.name)[1]
                    attach_filename = f"{withholding_data['withholding_receipt_number']}_{for_company.tin_number}_attachment{attach_ext}"
                    try:
                        attach_file.seek(0)
                        withholding_receipt.withholding_attachment.save(
                            name=attach_filename,
                            content=ContentFile(attach_file.read()),
                            save=True
                        )
                        logger.info(f"Withholding attachment saved: {withholding_receipt.withholding_attachment.path}")
                    except Exception as e:
                        withholding_receipt.delete()
                        logger.error(f"Failed to save withholding attachment: {str(e)}", exc_info=True)
                        raise DRFValidationError({"attachment": f"Failed to save attachment: {str(e)}"})

        # === Final ReceiptDocument ===
        receipt_doc = ReceiptDocument.objects.create(
            main_receipt=main_receipt,
            withholding_receipt=withholding_receipt,
            for_company=for_company,
            uploaded_by_contact=uploaded_by,
            notes=notes,
            status='uploaded'
        )

        return receipt_doc

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if not request or not hasattr(request, "FILES"):
            raise DRFValidationError("Request must include file data.")

        main_data = validated_data.pop("main_receipt_data", None)
        withholding_data = validated_data.pop("withholding_receipt_data", None)

        # === Update Main Receipt ===
        if main_data:
            main_file_key = "main_receipt_data.main_receipt"
            if main_file_key not in request.FILES:
                raise DRFValidationError({"main_receipt_data": f"File '{main_file_key}' is required."})

            main_file = request.FILES[main_file_key]
            file_content = main_file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            main_file.seek(0)

            if MainReceiptDocument.objects.exclude(pk=instance.main_receipt.pk).filter(main_receipt_hash=file_hash).exists():
                raise DRFValidationError({"file": "This file was already uploaded."})

            main_data["main_receipt_filename"] = get_valid_filename(main_file.name)
            main_data["main_receipt_content_type"] = main_file.content_type or "application/octet-stream"
            main_data["main_receipt_hash"] = file_hash

            attach_key = "main_receipt_data.attachment"
            if attach_key in request.FILES:
                attach_file = request.FILES[attach_key]
                main_data["attachment_filename"] = get_valid_filename(attach_file.name)
                main_data["attachment_content_type"] = attach_file.content_type or "application/octet-stream"

            main_data["company_tin"] = instance.for_company.tin_number

            # Delete old files
            if instance.main_receipt.main_receipt:
                try:
                    default_storage.delete(instance.main_receipt.main_receipt.path)
                    logger.info(f"Deleted old main receipt: {instance.main_receipt.main_receipt.path}")
                except Exception as e:
                    logger.error(f"Failed to delete old main receipt: {str(e)}")

            if instance.main_receipt.attachment:
                try:
                    default_storage.delete(instance.main_receipt.attachment.path)
                    logger.info(f"Deleted old attachment: {instance.main_receipt.attachment.path}")
                except Exception as e:
                    logger.error(f"Failed to delete old attachment: {str(e)}")

            # Update fields
            for key, value in main_data.items():
                setattr(instance.main_receipt, key, value)

            # Save new main file
            ext = os.path.splitext(main_file.name)[1]
            filename = f"{main_data['receipt_number']}_{instance.for_company.tin_number}{ext}"
            try:
                main_file.seek(0)
                instance.main_receipt.main_receipt.save(
                    name=filename,
                    content=ContentFile(main_file.read()),
                    save=False
                )
            except Exception as e:
                logger.error(f"Failed to save updated main receipt: {str(e)}", exc_info=True)
                raise DRFValidationError({"file": f"Failed to save file: {str(e)}"})

            # Save attachment
            if attach_key in request.FILES:
                attach_file = request.FILES[attach_key]
                attach_ext = os.path.splitext(attach_file.name)[1]
                attach_filename = f"{main_data['receipt_number']}_{instance.for_company.tin_number}_attachment{attach_ext}"
                try:
                    attach_file.seek(0)
                    instance.main_receipt.attachment.save(
                        name=attach_filename,
                        content=ContentFile(attach_file.read()),
                        save=False
                    )
                except Exception as e:
                    logger.error(f"Failed to save updated attachment: {str(e)}", exc_info=True)
                    raise DRFValidationError({"attachment": f"Failed to save attachment: {str(e)}"})

            instance.main_receipt.save()

        elif "main_receipt" in validated_data:
            instance.main_receipt = validated_data.pop("main_receipt")

        # === Update Withholding Receipt ===
        if withholding_data is not None:
            wht_file_key = "withholding_receipt_data.withholding_receipt"
            if wht_file_key in request.FILES:
                wht_file = request.FILES[wht_file_key]
                withholding_data["withholding_receipt_filename"] = get_valid_filename(wht_file.name)
                withholding_data["withholding_receipt_content_type"] = wht_file.content_type or "application/octet-stream"

                wht_attach_key = "withholding_receipt_data.withholding_attachment"
                if wht_attach_key in request.FILES:
                    attach_file = request.FILES[wht_attach_key]
                    withholding_data["withholding_attachment_filename"] = get_valid_filename(attach_file.name)
                    withholding_data["withholding_attachment_content_type"] = attach_file.content_type or "application/octet-stream"

                if "withholding_receipt_number" not in withholding_data:
                    raise DRFValidationError({
                        "withholding_receipt_data": "Field 'withholding_receipt_number' is required."
                    })

                withholding_data["company_tin"] = instance.for_company.tin_number

                if instance.withholding_receipt:
                    # Delete old files
                    if instance.withholding_receipt.withholding_receipt:
                        try:
                            default_storage.delete(instance.withholding_receipt.withholding_receipt.path)
                            logger.info(f"Deleted old withholding receipt: {instance.withholding_receipt.withholding_receipt.path}")
                        except Exception as e:
                            logger.error(f"Failed to delete old withholding receipt: {str(e)}")

                    if instance.withholding_receipt.withholding_attachment:
                        try:
                            default_storage.delete(instance.withholding_receipt.withholding_attachment.path)
                            logger.info(f"Deleted old attachment: {instance.withholding_receipt.withholding_attachment.path}")
                        except Exception as e:
                            logger.error(f"Failed to delete old attachment: {str(e)}")

                    # Update fields
                    for key, value in withholding_data.items():
                        setattr(instance.withholding_receipt, key, value)

                    # Save new file
                    ext = os.path.splitext(wht_file.name)[1]
                    filename = f"{withholding_data['withholding_receipt_number']}_{instance.for_company.tin_number}{ext}"
                    try:
                        wht_file.seek(0)
                        instance.withholding_receipt.withholding_receipt.save(
                            name=filename,
                            content=ContentFile(wht_file.read()),
                            save=False
                        )
                    except Exception as e:
                        logger.error(f"Failed to save updated withholding receipt: {str(e)}", exc_info=True)
                        raise DRFValidationError({"file": f"Failed to save file: {str(e)}"})

                    # Save attachment
                    if wht_attach_key in request.FILES:
                        attach_file = request.FILES[wht_attach_key]
                        attach_ext = os.path.splitext(attach_file.name)[1]
                        attach_filename = f"{withholding_data['withholding_receipt_number']}_{instance.for_company.tin_number}_attachment{attach_ext}"
                        try:
                            attach_file.seek(0)
                            instance.withholding_receipt.withholding_attachment.save(
                                name=attach_filename,
                                content=ContentFile(attach_file.read()),
                                save=False
                            )
                        except Exception as e:
                            logger.error(f"Failed to save updated attachment: {str(e)}", exc_info=True)
                            raise DRFValidationError({"attachment": f"Failed to save attachment: {str(e)}"})

                    instance.withholding_receipt.save()
                else:
                    # Create new withholding receipt
                    withholding_receipt = WithholdingReceiptDocument(**withholding_data)
                    withholding_receipt.save()

                    ext = os.path.splitext(wht_file.name)[1]
                    filename = f"{withholding_data['withholding_receipt_number']}_{instance.for_company.tin_number}{ext}"
                    try:
                        wht_file.seek(0)
                        withholding_receipt.withholding_receipt.save(
                            name=filename,
                            content=ContentFile(wht_file.read()),
                            save=False
                        )
                    except Exception as e:
                        withholding_receipt.delete()
                        logger.error(f"Failed to save new withholding receipt: {str(e)}", exc_info=True)
                        raise DRFValidationError({"file": f"Failed to save file: {str(e)}"})

                    if wht_attach_key in request.FILES:
                        attach_file = request.FILES[wht_attach_key]
                        attach_ext = os.path.splitext(attach_file.name)[1]
                        attach_filename = f"{withholding_data['withholding_receipt_number']}_{instance.for_company.tin_number}_attachment{attach_ext}"
                        try:
                            attach_file.seek(0)
                            withholding_receipt.withholding_attachment.save(
                                name=attach_filename,
                                content=ContentFile(attach_file.read()),
                                save=False
                            )
                        except Exception as e:
                            withholding_receipt.delete()
                            logger.error(f"Failed to save new attachment: {str(e)}", exc_info=True)
                            raise DRFValidationError({"attachment": f"Failed to save attachment: {str(e)}"})

                    withholding_receipt.save()
                    instance.withholding_receipt = withholding_receipt

        instance.save()
        return instance


class ReceiptDocumentDetailSerializer(serializers.ModelSerializer):
    main_receipt = MainReceiptDocumentSerializer(read_only=True)
    withholding_receipt = WithholdingReceiptDocumentSerializer(read_only=True)

    class Meta:
        model = ReceiptDocument
        fields = ["id", "main_receipt", "withholding_receipt", "uploaded_at"]