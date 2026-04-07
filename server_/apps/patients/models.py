import uuid
from django.db import models
from apps.settings_module.models import Pharmacy
 
class Patient(models.Model):
    """Pharmacy portal patient. pharmacy_ prefix avoids collision with shared users table."""
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id       = models.UUIDField(unique=True, null=True, blank=True)  # links to shared users.id
    full_name     = models.CharField(max_length=255)
    phone         = models.CharField(max_length=20, unique=True)
    email         = models.EmailField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nhif_number   = models.CharField(max_length=50, blank=True)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    class Meta:
        managed  = True                   # Django creates this table
        db_table = 'pharmacy_patients'
    def __str__(self): return f'{self.full_name} ({self.phone})'
 
 
class PatientPrescription(models.Model):
    REFILL_STATUS=[('AVAILABLE','Available'),('PENDING','Pending'),
                   ('PROCESSING','Processing'),('READY','Ready'),
                   ('COMPLETED','Completed'),('EXPIRED','Expired')]
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient           = models.ForeignKey(Patient, on_delete=models.CASCADE,
                          related_name='prescriptions')
    prescription_id   = models.UUIDField()   # points at shared prescriptions.id — NOT a Django FK
    is_chronic        = models.BooleanField(default=False)
    refill_status     = models.CharField(max_length=20, choices=REFILL_STATUS, default='AVAILABLE')
    refills_remaining = models.PositiveIntegerField(default=0)
    last_refill_date  = models.DateField(null=True, blank=True)
    next_refill_date  = models.DateField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    class Meta:
        managed  = True
        db_table = 'pharmacy_patient_prescriptions'
 
 
class RefillRequest(models.Model):
    STATUS=[('PENDING','Pending'),('PHARMACY_SELECTED','Pharmacy Selected'),
            ('LOCATION_SET','Location Set'),('PAYMENT_PENDING','Payment Pending'),
            ('PAID','Paid'),('PROCESSING','Processing'),('READY','Ready'),
            ('DELIVERED','Delivered'),('CANCELLED','Cancelled')]
    DELIVERY_TYPE=[('pickup','Pickup'),('home_delivery','Home Delivery')]
    id                   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient              = models.ForeignKey(Patient, on_delete=models.CASCADE,
                             related_name='refill_requests')
    patient_prescription = models.ForeignKey(PatientPrescription, on_delete=models.CASCADE)
    selected_pharmacy    = models.ForeignKey(Pharmacy, on_delete=models.SET_NULL, null=True, blank=True)
    status               = models.CharField(max_length=25, choices=STATUS, default='PENDING')
    delivery_type        = models.CharField(max_length=20, choices=DELIVERY_TYPE, default='pickup')
    delivery_address     = models.TextField(blank=True)
    delivery_lat         = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_lng         = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    total_amount         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes                = models.TextField(blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)
    class Meta:
        managed  = True
        db_table = 'pharmacy_refill_requests'
        ordering = ['-created_at']
 
 
class MpesaTransaction(models.Model):
    STATUS=[('PENDING','Pending'),('SUCCESS','Success'),
            ('FAILED','Failed'),('CANCELLED','Cancelled')]
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refill_request      = models.ForeignKey(RefillRequest, on_delete=models.CASCADE,
                            related_name='transactions')
    patient             = models.ForeignKey(Patient, on_delete=models.CASCADE)
    phone               = models.CharField(max_length=20)
    amount              = models.DecimalField(max_digits=10, decimal_places=2)
    status              = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_no    = models.CharField(max_length=50, blank=True)
    result_code         = models.IntegerField(null=True, blank=True)
    result_desc         = models.TextField(blank=True)
    initiated_at        = models.DateTimeField(auto_now_add=True)
    completed_at        = models.DateTimeField(null=True, blank=True)
    class Meta:
        managed  = True
        db_table = 'pharmacy_mpesa_transactions'
