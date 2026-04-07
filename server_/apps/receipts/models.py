import uuid
from django.db import models


class Receipt(models.Model):
    PAYMENT_METHOD = [
        ('mpesa', 'M-Pesa'), ('cash', 'Cash'),
        ('insurance', 'Insurance'), ('nhif', 'NHIF'),
    ]
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # FK stored as UUID — TiDB manages the FK to orders.id
    order_id       = models.UUIDField(unique=True)
    # FK stored as UUID — TiDB manages the FK to users.id (role=pharmacist)
    dispensed_by   = models.UUIDField(null=True, blank=True)
    # Amounts — column names match TiDB exactly (subtotal, discount, total)
    subtotal       = models.DecimalField(max_digits=10, decimal_places=2)
    discount       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total          = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    mpesa_ref      = models.CharField(max_length=50, null=True, blank=True)
    pdf_path       = models.CharField(max_length=500, null=True, blank=True)
    emailed_at     = models.DateTimeField(null=True, blank=True)
    sms_sent_at    = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'receipts'
