from django.db import models
from django.core.validators import RegexValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class Contact(models.Model):
    name = models.CharField(max_length=200)
    
    # ✅ TIN: required, 10 digits, no spaces
    tin_number = models.CharField(
        max_length=10,
        blank=False,  # ✅ Required
        null=False,   # ✅ Not null
        help_text="10-digit Ethiopian TIN (e.g., 1234567890)",
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message="TIN must be exactly 10 digits (numbers only).",
                code="invalid_tin"
            )
        ],
        db_index=True  # ✅ Faster lookups by TIN
    )

    # 🟢 Unchanged: simple text field for address
    address = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        # ✅ Prevent duplicate TINs
        unique_together = [('tin_number',)]

    def clean(self):
        """Run validation before save"""
        super().clean()

        if self.tin_number:
            # Strip whitespace
            self.tin_number = self.tin_number.strip()

            # Re-validate (in case bypassed via admin or direct save)
            validator = RegexValidator(r'^\d{10}$', "TIN must be exactly 10 digits.")
            try:
                validator(self.tin_number)
            except ValidationError:
                raise ValidationError({"tin_number": "TIN must be exactly 10 digits (numbers only)."})

    def save(self, *args, **kwargs):
        # ✅ Always run full clean (including clean() and field validators)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (TIN: {self.tin_number})"