import uuid
from django.db import models
from apps.settings_module.models import Pharmacy


class Supplier(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    email        = models.EmailField(null=True, blank=True)
    phone        = models.CharField(max_length=20, null=True, blank=True)
    address      = models.TextField(null=True, blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'suppliers'

    def __str__(self):
        return self.name


class BulkOrder(models.Model):
    STATUS = [
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('acknowledged', 'Acknowledged'),
        ('partially_received', 'Partially Received'), ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacy      = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, db_column='pharmacy_id')
    supplier      = models.ForeignKey(Supplier, on_delete=models.PROTECT, db_column='supplier_id')
    # FK stored as UUID — TiDB manages FK to users.id (role=pharmacist/pharmacy_manager)
    created_by    = models.UUIDField(null=True, blank=True)
    status        = models.CharField(max_length=25, choices=STATUS, default='draft')
    total_cost    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expected_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    notes         = models.TextField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'bulk_orders'


class BulkOrderItem(models.Model):
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bulk_order        = models.ForeignKey(BulkOrder, on_delete=models.CASCADE,
                          related_name='items', db_column='bulk_order_id')
    # FK stored as UUID — TiDB manages FK to drugs.id
    drug_id           = models.UUIDField()
    quantity_ordered  = models.IntegerField()
    quantity_received = models.IntegerField(default=0)
    unit_cost         = models.DecimalField(max_digits=10, decimal_places=2)
    batch_number      = models.CharField(max_length=100, null=True, blank=True)
    expiry_date       = models.DateField(null=True, blank=True)

    class Meta:
        managed  = False
        db_table = 'bulk_order_items'
