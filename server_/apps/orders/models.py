import uuid
from django.db import models
from apps.settings_module.models import Pharmacy
 
class Order(models.Model):
    STATUS        =[('pending','Pending'),('processing','Processing'),('ready','Ready'),
                    ('dispatched','Dispatched'),('delivered','Delivered'),('cancelled','Cancelled')]
    PAYMENT_STATUS=[('unpaid','Unpaid'),('paid','Paid'),('refunded','Refunded')]
    PAYMENT_METHOD=[('mpesa','M-Pesa'),('cash','Cash'),('insurance','Insurance'),('nhif','NHIF')]
    DELIVERY_TYPE =[('pickup','Pickup'),('home_delivery','Home Delivery')]
    PRIORITY      =[('normal','Normal'),('urgent','Urgent')]
 
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number    = models.CharField(max_length=100, unique=True)
    prescription_id = models.UUIDField(null=True, blank=True)
    pharmacy        = models.ForeignKey(Pharmacy, on_delete=models.PROTECT, db_column='pharmacy_id')
    prepared_by     = models.UUIDField(null=True, blank=True)
    patient_id      = models.UUIDField(null=True, blank=True)
    # Snapshot columns
    patient_name    = models.CharField(max_length=255)
    patient_phone   = models.CharField(max_length=20, null=True, blank=True)
    patient_address = models.TextField(null=True, blank=True)
    delivery_type   = models.CharField(max_length=20, choices=DELIVERY_TYPE, default='pickup')
    priority        = models.CharField(max_length=10, choices=PRIORITY, default='normal')
    status          = models.CharField(max_length=20, choices=STATUS, default='pending')
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status  = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='unpaid')
    payment_method  = models.CharField(max_length=20, choices=PAYMENT_METHOD, null=True, blank=True)
    mpesa_ref       = models.CharField(max_length=50, null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
 
    class Meta:
        managed  = False
        db_table = 'orders'
        ordering = ['-created_at']

class OrderItem(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id   = models.CharField(max_length=36)
    drug_id    = models.CharField(max_length=36)
    drug_name  = models.CharField(max_length=255)
    dosage     = models.CharField(max_length=100, null=True, blank=True)
    frequency  = models.CharField(max_length=100, null=True, blank=True)
    quantity   = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed  = False
        db_table = 'order_items'

class PDispatchedItem(models.Model):
    DOSAGE_FORM = [
        ('tablet','Tablet'),('capsule','Capsule'),('syrup','Syrup'),
        ('injection','Injection'),('cream','Cream'),('drops','Drops'),
        ('inhaler','Inhaler'),('patch','Patch'),('other','Other'),
    ]
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_id      = models.CharField(max_length=36)
    prescription_id = models.CharField(max_length=36, null=True, blank=True)
    pharmacy_id     = models.CharField(max_length=36, null=True, blank=True)
    prescribed_by   = models.CharField(max_length=36, null=True, blank=True)
    dispensed_by    = models.CharField(max_length=36, null=True, blank=True)
    drug_id         = models.CharField(max_length=36, null=True, blank=True)
    drug_name       = models.CharField(max_length=255)
    dosage          = models.CharField(max_length=100, null=True, blank=True)
    dosage_form     = models.CharField(max_length=20, choices=DOSAGE_FORM, null=True, blank=True)
    frequency       = models.CharField(max_length=100, null=True, blank=True)
    times_per_day   = models.IntegerField(null=True, blank=True)
    dosage_timing   = models.JSONField(null=True, blank=True)
    with_food       = models.BooleanField(default=False, null=True, blank=True)
    route           = models.CharField(max_length=50, null=True, blank=True)
    instructions    = models.TextField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'p_dispatched'