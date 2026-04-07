import uuid
from django.db import models


class Prescription(models.Model):
    STATUS   = [
        ('draft', 'Draft'), ('pending', 'Pending'), ('validated', 'Validated'),
        ('rejected', 'Rejected'), ('dispensed', 'Dispensed'), ('delivered', 'Delivered'),
    ]
    PRIORITY = [('normal', 'Normal'), ('urgent', 'Urgent')]

    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    patient_id          = models.CharField(max_length=36)
    doctor_id           = models.CharField(max_length=36)
    pharmacy_id         = models.CharField(max_length=36, null=True, blank=True)  # ← CharField
    dispensed_by        = models.CharField(max_length=36, null=True, blank=True)
    patient_name        = models.CharField(max_length=255)
    patient_phone       = models.CharField(max_length=20, null=True, blank=True)
    patient_address     = models.CharField(max_length=255, null=True, blank=True)
    doctor_name         = models.CharField(max_length=255)
    diagnosis           = models.TextField(null=True, blank=True)
    notes               = models.TextField(null=True, blank=True)
    priority            = models.CharField(max_length=10, choices=PRIORITY, default='normal')
    issue_date          = models.DateField()
    expiry_date         = models.DateField(null=True, blank=True)
    items               = models.JSONField(default=list)
    status              = models.CharField(max_length=20, choices=STATUS, default='draft')
    rejection_reason    = models.TextField(null=True, blank=True)
    dispensed_at        = models.DateTimeField(null=True, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'prescriptions'
        ordering = ['-created_at']