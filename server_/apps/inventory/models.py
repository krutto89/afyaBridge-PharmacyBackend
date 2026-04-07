import uuid
from django.db import models


class Drug(models.Model):
    CATEGORIES = [
        ('antibiotic', 'Antibiotic'), ('analgesic', 'Analgesic'),
        ('chronic', 'Chronic'),       ('vitamin', 'Vitamin/Supplement'),
        ('antifungal', 'Antifungal'), ('other', 'Other'),
    ]
    UNITS = [
        ('tablet', 'Tablet'), ('capsule', 'Capsule'), ('bottle', 'Bottle'),
        ('vial', 'Vial'),     ('sachet', 'Sachet'),   ('tube', 'Tube'),
    ]

    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacy_id       = models.CharField(max_length=36)   # ← CharField not ForeignKey
    drug_name         = models.CharField(max_length=255)
    generic_name      = models.CharField(max_length=255, null=True, blank=True)
    category          = models.CharField(max_length=50, choices=CATEGORIES)
    unit              = models.CharField(max_length=30, choices=UNITS, default='tablet')
    unit_price        = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_in_stock = models.IntegerField(default=0)
    reorder_level     = models.IntegerField(default=20)
    critical_level    = models.IntegerField(default=5)
    requires_rx       = models.BooleanField(default=True)
    is_active         = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'drugs'
        ordering = ['drug_name']

    @property
    def stock_status(self):
        if self.quantity_in_stock <= self.critical_level: return 'CRITICAL'
        if self.quantity_in_stock <= self.reorder_level:  return 'LOW'
        return 'OK'


class StockBatch(models.Model):
    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drug_id            = models.CharField(max_length=36)  # ← CharField not ForeignKey
    supplier_id        = models.CharField(max_length=36, null=True, blank=True)
    bulk_order_id      = models.CharField(max_length=36, null=True, blank=True)
    received_by        = models.CharField(max_length=36, null=True, blank=True)
    batch_number       = models.CharField(max_length=100)
    quantity_received  = models.IntegerField()
    quantity_remaining = models.IntegerField()
    manufacture_date   = models.DateField(null=True, blank=True)
    expiry_date        = models.DateField()
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'stock_batches'
        ordering = ['expiry_date']