from django.db import models

class ReceiptName(models.Model):  #cash vat cash tot cash exmpted, credit vat credit tot, credit exempted 
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name.upper()

    def save(self, *args, **kwargs):
        self.name = self.name.upper().strip()
        super().save(*args, **kwargs)
        
class ReceiptKind(models.Model):  #manual digital electronics and other
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name.title()

    def save(self, *args, **kwargs):
        self.name = self.name.title().strip()
        super().save(*args, **kwargs)
class ReceiptCatagory(models.Model):  #income expense
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name.title()

    def save(self, *args, **kwargs):
        self.name = self.name.title().strip()
        super().save(*args, **kwargs)
class ReceiptType(models.Model):
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name.title()

    def save(self, *args, **kwargs):
        self.name = self.name.title().strip()
        super().save(*args, **kwargs)
        
    
