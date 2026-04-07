import uuid
from django.db import models
 
class Pharmacy(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name           = models.CharField(max_length=255)
    email          = models.EmailField()
    phone          = models.CharField(max_length=20)
    logo           = models.CharField(max_length=500, null=True, blank=True)
    address_line1  = models.CharField(max_length=255)
    address_line2  = models.CharField(max_length=255, null=True, blank=True)
    county         = models.CharField(max_length=100)
    sub_county     = models.CharField(max_length=100, null=True, blank=True)
    gps_lat        = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng        = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    license_number = models.CharField(max_length=100)
    license_expiry = models.DateField()
    delivery_zones = models.JSONField(default=list, null=True, blank=True)
    is_24hr        = models.BooleanField(default=False)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)
    class Meta:
        managed  = False
        db_table = 'pharmacies'
    def __str__(self): return self.name
 
 
class PharmacyHours(models.Model):
    DAYS=[('MON','Mon'),('TUE','Tue'),('WED','Wed'),('THU','Thu'),
          ('FRI','Fri'),('SAT','Sat'),('SUN','Sun')]
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacy    = models.ForeignKey(Pharmacy, on_delete=models.CASCADE,
                    related_name='hours', db_column='pharmacy_id')
    day_of_week = models.CharField(max_length=3, choices=DAYS)
    open_time   = models.TimeField(null=True, blank=True)
    close_time  = models.TimeField(null=True, blank=True)
    is_closed   = models.BooleanField(default=False)
    class Meta:
        managed         = False
        db_table        = 'pharmacy_hours'
        unique_together = [('pharmacy', 'day_of_week')]
 
 
class NotificationPreference(models.Model):
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id             = models.UUIDField(unique=True)
    sms_enabled         = models.BooleanField(default=True)
    email_enabled       = models.BooleanField(default=True)
    push_enabled        = models.BooleanField(default=True)
    in_app_enabled      = models.BooleanField(default=True)
    appointment_alerts  = models.BooleanField(default=True)
    prescription_alerts = models.BooleanField(default=True)
    payment_alerts      = models.BooleanField(default=True)
    delivery_alerts     = models.BooleanField(default=True)
    chat_alerts         = models.BooleanField(default=True)
    broadcast_alerts    = models.BooleanField(default=True)
    low_stock_alerts    = models.BooleanField(default=True)
    expiry_alerts       = models.BooleanField(default=True)
    expiry_alert_days   = models.IntegerField(default=14)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)
    class Meta:
        managed  = False
        db_table = 'notification_preferences'
