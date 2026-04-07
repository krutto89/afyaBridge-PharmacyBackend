import uuid
from django.db import models


class Delivery(models.Model):
    STATUS = [
        ('pending', 'Pending'), ('assigned', 'Assigned'), ('accepted', 'Accepted'),
        ('picked_up', 'Picked Up'), ('out_for_delivery', 'Out For Delivery'),
        ('delivered', 'Delivered'), ('failed', 'Failed'), ('cancelled', 'Cancelled'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package_number = models.CharField(max_length=100, unique=True)
    order_id       = models.CharField(max_length=36, unique=True)   # ← changed
    rider_id       = models.CharField(max_length=36, null=True, blank=True)  # ← changed

    status                  = models.CharField(max_length=25, choices=STATUS, default='pending')
    accept_status           = models.BooleanField(default=False)
    pickup_location         = models.CharField(max_length=255, null=True, blank=True)
    pickup_lat              = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_lng              = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_contact          = models.CharField(max_length=20, null=True, blank=True)
    pickup_time             = models.DateTimeField(null=True, blank=True)
    dropoff_location        = models.CharField(max_length=255, null=True, blank=True)
    dropoff_lat             = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dropoff_lng             = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    receiver_contact        = models.CharField(max_length=20, null=True, blank=True)
    requirement             = models.CharField(max_length=255, null=True, blank=True)
    estimated_delivery_time = models.CharField(max_length=100, null=True, blank=True)
    distance                = models.FloatField(null=True, blank=True)
    charges                 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    delivery_zone           = models.CharField(max_length=100, null=True, blank=True)
    delivery_notes          = models.TextField(null=True, blank=True)
    otp_code                = models.CharField(max_length=6)
    delivered_at            = models.DateTimeField(null=True, blank=True)
    date_approved           = models.DateTimeField(null=True, blank=True)
    created_at              = models.DateTimeField(auto_now_add=True)
    updated_at              = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'deliveries'
        ordering = ['-created_at']