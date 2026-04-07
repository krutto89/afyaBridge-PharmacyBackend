from django.contrib import admin
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import PharmacyUser, OTPVerification, PharmacyRegistration


@admin.register(PharmacyUser)
class PharmacyUserAdmin(BaseUserAdmin):
    list_display    = ['email', 'full_name', 'role', 'account_status',
                       'is_active', 'is_verified', 'pharmacy_id', 'created_at']
    list_filter     = ['role', 'account_status', 'is_active', 'is_verified',
                       'two_factor_enabled']
    search_fields   = ['email', 'full_name', 'phone_number']
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'last_password_change']
    ordering        = ['-created_at']

    fieldsets = (
        ('Identity', {
            'fields': ('email', 'password_hash', 'full_name', 'role',
                       'phone_number', 'profile_image', 'initials')
        }),
        ('Status & Auth', {
            'fields': ('is_active', 'is_verified', 'account_status', 'status_reason',
                       'two_factor_enabled', 'two_factor_method', 'two_factor_phone',
                       'last_password_change', 'last_login')
        }),
        ('Profile', {
            'fields': ('bio', 'gender', 'date_of_birth', 'age', 'blood_type',
                       'address', 'provider_sharing', 'research_opt_in'),
            'classes': ('collapse',)
        }),
        ('Doctor Fields', {
            'fields': ('specialty', 'kmpdc_license', 'hospital', 'consultation_fee',
                       'allow_video_consultations', 'allow_in_person_consultations',
                       'working_hours', 'slot_duration', 'auto_confirm_appointments',
                       'rating', 'total_reviews', 'verification_status',
                       'verified_at', 'verified_by'),
            'classes': ('collapse',)
        }),
        ('Rider Fields', {
            'fields': ('national_id', 'vehicle_type', 'plate_number',
                       'driving_license_no', 'license_expiry', 'id_verified',
                       'license_verified', 'approved_status', 'date_approved',
                       'on_duty', 'emergency_contact', 'orders_made', 'verified_by_admin'),
            'classes': ('collapse',)
        }),
        ('Pharmacy Link', {
            'fields': ('pharmacy_id',)
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password_hash'),
        }),
    )
    # BaseUserAdmin expects 'password' but our model uses password_hash
    # Override to avoid errors
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display  = ['phone', 'email', 'purpose', 'is_used', 'expires_at', 'created_at']
    list_filter   = ['purpose', 'is_used']
    search_fields = ['phone', 'email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PharmacyRegistration)
class PharmacyRegistrationAdmin(admin.ModelAdmin):
    list_display  = ['pharmacy_name_legal', 'business_email', 'status',
                     'current_step', 'submitted_at', 'created_at']
    list_filter   = ['status']
    search_fields = ['pharmacy_name_legal', 'business_email', 'ppb_license_no']
    readonly_fields = ['created_at', 'updated_at', 'submitted_at']

    fieldsets = (
        ('Business Info', {
            'fields': ('pharmacy_name_legal', 'trading_name', 'business_reg_no',
                       'kra_pin', 'ppb_license_no', 'license_expiry')
        }),
        ('Location', {
            'fields': ('county', 'sub_county', 'physical_address', 'gps_lat', 'gps_lng')
        }),
        ('Contact', {
            'fields': ('business_phone', 'business_email', 'phone_verified', 'email_verified')
        }),
        ('Lead Pharmacist', {
            'fields': ('pharmacist_name', 'id_or_passport_no', 'pharmacist_reg_no',
                       'practicing_license', 'practicing_expiry',
                       'pharmacist_phone', 'pharmacist_email'),
            'classes': ('collapse',)
        }),
        ('Documents', {
            'fields': ('id_document', 'practicing_license_doc', 'operating_license_doc',
                       'business_reg_cert', 'kra_pin_cert', 'proof_of_address_doc'),
            'classes': ('collapse',)
        }),
        ('Payment', {
            'fields': ('mpesa_method', 'short_code_name', 'short_code_number',
                       'settlement_bank', 'settlement_frequency'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'current_step', 'submitted_at',
                       'reviewed_by', 'review_notes', 'created_at', 'updated_at')
        }),
    )
