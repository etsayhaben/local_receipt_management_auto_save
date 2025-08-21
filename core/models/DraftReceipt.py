# core/models/draft.py

from django.db import models
import uuid
from core.models.contact import Contact

class DraftReceipt(models.Model):
    """
    Stores temporary receipt data while being filled out.
    One draft per (company, uploaded_document_number).
    Used for autosave and recovery after power loss.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique ID for this draft"
    )

    # Who: the company creating the receipt (recorded_by)
    company = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='draft_receipts',
        help_text="The company (recorded_by) creating this receipt"
    )

    # What: links to the uploaded document
    uploaded_document_number = models.CharField(
        max_length=90,
        help_text="Original receipt number from upload (e.g., 246)"
    )

    # Optional: final receipt number being created (e.g., FS246, M751)
    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="The receipt number the clerk is creating (e.g., FS246)"
    )

    # ✅ Use models.JSONField instead
    data = models.JSONField(
        help_text="Full draft data: issued_by, items, totals, etc."
    )

    # State
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('discarded', 'Discarded')
        ],
        default='draft',
        help_text="Current state of the draft"
    )

    # For conflict detection
    revision = models.PositiveIntegerField(
        default=0,
        help_text="Incremented on each save. Used for optimistic concurrency."
    )

    # When
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'uploaded_document_number'],
                name='unique_draft_per_company_per_upload'
            )
        ]
        indexes = [
            models.Index(fields=['company', 'uploaded_document_number']),
            models.Index(fields=['receipt_number']),
            models.Index(fields=['company', 'status']),
            models.Index(fields=['updated_at']),
        ]
        db_table = 'receipt_drafts'
        verbose_name = "Draft Receipt"
        verbose_name_plural = "Draft Receipts"

    def __str__(self):
        return (
            f"📝 Draft: {self.uploaded_document_number} "
            f"→ {self.receipt_number or 'No number'} "
            f"| {self.company.name}"
        )