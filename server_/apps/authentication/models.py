import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# add at top
from apps.settings_module.models import Pharmacy

class PharmacyUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('role', 'admin')
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)


class PharmacyUser(AbstractBaseUser, PermissionsMixin):
    ROLES = [
        ('patient', 'Patient'), ('doctor', 'Doctor'),
        ('pharmacist', 'Pharmacist'), ('rider', 'Rider'), ('admin', 'Admin'),
    ]
    ACCOUNT_STATUS = [
        ('active', 'Active'), ('suspended', 'Suspended'),
        ('locked', 'Locked'), ('disabled', 'Disabled'),
    ]
    TWO_FACTOR_METHOD = [('sms', 'SMS'), ('email', 'Email'), ('app', 'App')]
    VERIFICATION_STATUS = [
        ('pending_verification', 'Pending Verification'),
        ('verified', 'Verified'), ('rejected', 'Rejected'),
    ]
    APPROVED_STATUS = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role                  = models.CharField(max_length=30, choices=ROLES)
    full_name             = models.CharField(max_length=255)
    email                 = models.EmailField(unique=True)
    password_hash         = models.CharField(max_length=255)
    phone_number          = models.CharField(max_length=20, unique=True, null=True, blank=True)
    profile_image         = models.CharField(max_length=500, null=True, blank=True)
    initials              = models.CharField(max_length=10, null=True, blank=True)

    is_active             = models.BooleanField(default=True)
    is_verified           = models.BooleanField(default=False)
    two_factor_enabled    = models.BooleanField(default=False)
    two_factor_method     = models.CharField(max_length=10, choices=TWO_FACTOR_METHOD, default='sms', null=True, blank=True)
    two_factor_phone      = models.CharField(max_length=20, null=True, blank=True)
    last_password_change  = models.DateTimeField(null=True, blank=True)
    last_login            = models.DateTimeField(null=True, blank=True)
    account_status        = models.CharField(max_length=20, choices=ACCOUNT_STATUS, default='active')
    status_reason         = models.CharField(max_length=255, null=True, blank=True)

    bio                   = models.TextField(null=True, blank=True)
    gender                = models.CharField(max_length=20, null=True, blank=True)
    date_of_birth         = models.CharField(max_length=50, null=True, blank=True)
    age                   = models.IntegerField(null=True, blank=True)
    blood_type            = models.CharField(max_length=10, null=True, blank=True)
    address               = models.CharField(max_length=255, null=True, blank=True)

    provider_sharing      = models.BooleanField(default=True, null=True, blank=True)
    research_opt_in       = models.BooleanField(default=False, null=True, blank=True)

    emergency_contacts    = models.JSONField(null=True, blank=True)
    allergies             = models.JSONField(null=True, blank=True)
    surgeries             = models.JSONField(null=True, blank=True)
    visits                = models.JSONField(null=True, blank=True)
    conditions            = models.JSONField(null=True, blank=True)
    documents             = models.JSONField(null=True, blank=True)

    specialty                     = models.CharField(max_length=255, null=True, blank=True)
    kmpdc_license                 = models.CharField(max_length=100, null=True, blank=True)
    hospital                      = models.CharField(max_length=255, null=True, blank=True)
    consultation_fee              = models.FloatField(null=True, blank=True)
    allow_video_consultations     = models.BooleanField(null=True, blank=True)
    allow_in_person_consultations = models.BooleanField(null=True, blank=True)
    working_hours                 = models.JSONField(null=True, blank=True)
    slot_duration                 = models.IntegerField(null=True, blank=True)
    auto_confirm_appointments     = models.BooleanField(null=True, blank=True)
    rating                        = models.FloatField(default=0, null=True, blank=True)
    total_reviews                 = models.IntegerField(default=0, null=True, blank=True)
    verification_status           = models.CharField(max_length=30, choices=VERIFICATION_STATUS, null=True, blank=True)
    verified_at                   = models.DateTimeField(null=True, blank=True)
    verified_by                   = models.CharField(max_length=100, null=True, blank=True)

    national_id        = models.CharField(max_length=50, null=True, blank=True)
    vehicle_type       = models.CharField(max_length=100, null=True, blank=True)
    plate_number       = models.CharField(max_length=50, null=True, blank=True)
    driving_license_no = models.CharField(max_length=100, null=True, blank=True)
    license_expiry     = models.DateTimeField(null=True, blank=True)
    id_verified        = models.BooleanField(default=False, null=True, blank=True)
    license_verified   = models.BooleanField(default=False, null=True, blank=True)
    approved_status    = models.CharField(max_length=20, choices=APPROVED_STATUS, null=True, blank=True)
    date_approved      = models.DateTimeField(null=True, blank=True)
    on_duty            = models.BooleanField(default=False, null=True, blank=True)
    emergency_contact  = models.CharField(max_length=100, null=True, blank=True)
    orders_made        = models.IntegerField(default=0, null=True, blank=True)
    verified_by_admin  = models.BooleanField(default=False, null=True, blank=True)

    pharmacy = models.ForeignKey(
        'settings_module.Pharmacy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='pharmacy_id',
        related_name='users'
    )

    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name', 'role']
    objects = PharmacyUserManager()

    class Meta:
        managed  = False
        db_table = 'users'

    @property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self, value):
        self.password_hash = value

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    @property
    def is_staff(self):
        return self.role == 'admin'

    @property
    def is_superuser(self):
        return self.role == 'admin'

    # @property
    # def pharmacy(self):
    #     if not self.pharmacy_id:
    #         return None
    #     from apps.settings_module.models import Pharmacy
    #     try:
    #         return Pharmacy.objects.get(id=self.pharmacy_id)
    #     except Pharmacy.DoesNotExist:
    #         return None


class OTPVerification(models.Model):
    PURPOSE = [
        ('registration', 'Registration'),
        ('login', 'Login'),
        ('password_reset', 'Password Reset'),
        ('delivery_confirmation', 'Delivery Confirmation'),
    ]
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone      = models.CharField(max_length=20, null=True, blank=True)
    email      = models.EmailField(null=True, blank=True)
    otp_code   = models.CharField(max_length=6)
    purpose    = models.CharField(max_length=30, choices=PURPOSE)
    is_used    = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'otp_verifications'


class PharmacyRegistration(models.Model):
    STATUS           = [('draft','Draft'),('submitted','Submitted'),
                        ('under_review','Under Review'),('approved','Approved'),('rejected','Rejected')]
    MPESA_METHOD     = [('PAYBILL','Paybill'),('TILL','Till')]
    SETTLEMENT_FREQ  = [('DAILY','Daily'),('WEEKLY','Weekly'),('MONTHLY','Monthly')]

    id                     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacy_name_legal    = models.CharField(max_length=255)
    trading_name           = models.CharField(max_length=255, null=True, blank=True)
    business_reg_no        = models.CharField(max_length=100)
    kra_pin                = models.CharField(max_length=20)
    ppb_license_no         = models.CharField(max_length=100)
    license_expiry         = models.DateField()
    county                 = models.CharField(max_length=100)
    sub_county             = models.CharField(max_length=100, null=True, blank=True)
    physical_address       = models.TextField()
    gps_lat                = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng                = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    business_phone         = models.CharField(max_length=20)
    business_email         = models.EmailField()
    phone_verified         = models.BooleanField(default=False)
    email_verified         = models.BooleanField(default=False)
    pharmacist_name        = models.CharField(max_length=255, null=True, blank=True)
    id_or_passport_no      = models.CharField(max_length=50, null=True, blank=True)
    pharmacist_reg_no      = models.CharField(max_length=100, null=True, blank=True)
    practicing_license     = models.CharField(max_length=100, null=True, blank=True)
    practicing_expiry      = models.DateField(null=True, blank=True)
    pharmacist_phone       = models.CharField(max_length=20, null=True, blank=True)
    pharmacist_email       = models.EmailField(null=True, blank=True)

    id_document = models.FileField(
        upload_to='registration/id_docs/',
        null=True,
        blank=True
    )

    practicing_license_doc = models.FileField(
        upload_to='registration/practicing_licenses/',
        null=True,
        blank=True
    )

    operating_license_doc = models.FileField(
        upload_to='registration/operating_licenses/',
        null=True,
        blank=True
    )

    business_reg_cert = models.FileField(
        upload_to='registration/business_certs/',
        null=True,
        blank=True
    )

    kra_pin_cert = models.FileField(
        upload_to='registration/kra_certs/',
        null=True,
        blank=True
    )

    proof_of_address_doc = models.FileField(
        upload_to='registration/address_proofs/',
        null=True,
        blank=True
    )

    mpesa_method           = models.CharField(max_length=10, choices=MPESA_METHOD, null=True, blank=True)
    short_code_name        = models.CharField(max_length=255, null=True, blank=True)
    short_code_number      = models.CharField(max_length=10, null=True, blank=True)
    settlement_bank        = models.CharField(max_length=100, null=True, blank=True)
    settlement_frequency   = models.CharField(max_length=10, choices=SETTLEMENT_FREQ, default='DAILY', null=True, blank=True)
    status                 = models.CharField(max_length=20, choices=STATUS, default='draft')
    current_step           = models.IntegerField(default=1)
    submitted_at           = models.DateTimeField(null=True, blank=True)
    reviewed_by            = models.UUIDField(null=True, blank=True)
    review_notes           = models.TextField(null=True, blank=True)
    created_at             = models.DateTimeField(auto_now_add=True)
    updated_at             = models.DateTimeField(auto_now=True)

    class Meta:
        managed  = False
        db_table = 'pharmacy_registrations'


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        'PharmacyUser',
        on_delete=models.CASCADE,
        related_name='notification_preference'
    )

    email_notifications = models.BooleanField(default=True)
    sms_notifications   = models.BooleanField(default=True)
    push_notifications  = models.BooleanField(default=True)

    new_order_alert     = models.BooleanField(default=True)
    prescription_alert  = models.BooleanField(default=True)
    payment_alert       = models.BooleanField(default=True)
    system_announcement = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'notification_preferences'

    def __str__(self):
        return f"Notification prefs for {self.user.email}"


# ==================== PASSWORD RESET MODEL (Added) ====================
class PasswordReset(models.Model):
    """Model for password reset requests"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'PharmacyUser',
        on_delete=models.CASCADE,
        related_name='password_resets'
    )
    token = models.CharField(max_length=255, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'password_resets'

    def __str__(self):
        return f"Password reset for {self.user.email}"