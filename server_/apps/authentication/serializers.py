from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from .models import PharmacyUser, NotificationPreference, PharmacyRegistration


# =============================================================================
# AUTH
# =============================================================================

class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user = PharmacyUser.objects.get(email=data['email'])
            if not user.check_password(data['password']):
                raise serializers.ValidationError('Invalid credentials')
            data['user'] = user
            return data
        except PharmacyUser.DoesNotExist:
            raise serializers.ValidationError('Invalid credentials')


class UserProfileSerializer(serializers.ModelSerializer):
    pharmacy_id = serializers.SerializerMethodField()

    class Meta:
        model  = PharmacyUser
        fields = ['id', 'email', 'full_name', 'phone_number', 'role', 'pharmacy_id', 'account_status', 'is_active']

    def get_pharmacy_id(self, obj):
        pid = obj.__dict__.get('pharmacy_id')
        return str(pid) if pid else None


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password     = serializers.CharField(required=True, min_length=8)


class OTPVerifySerializer(serializers.Serializer):
    phone    = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=6, min_length=6)


class NotificationPrefSerializer(serializers.ModelSerializer):
    class Meta:
        model        = NotificationPreference
        fields       = '__all__'
        read_only_fields = ['id', 'user', 'updated_at']


# =============================================================================
# MULTI-STEP REGISTRATION (backward compatible — old step endpoints)
# =============================================================================

class RegistrationStep1Serializer(serializers.ModelSerializer):
    """Step 1: Core pharmacy identity."""

    class Meta:
        model  = PharmacyRegistration
        fields = [
            'pharmacy_name_legal', 'trading_name',
            'business_reg_no', 'kra_pin',
            'ppb_license_no', 'license_expiry',
            'county', 'sub_county', 'physical_address',
            'gps_lat', 'gps_lng',
            'business_phone', 'business_email',
        ]

    def validate_kra_pin(self, value):
        import re
        v = value.upper()
        if not re.match(r'^[A-Z]\d{9}[A-Z]$', v):
            raise serializers.ValidationError(
                'Invalid KRA PIN. Format: one letter + 9 digits + one letter e.g. A004626956Z'
            )
        return v

    def validate_ppb_license_no(self, value):
        if value and not value.startswith('PPB/'):
            raise serializers.ValidationError('PPB License must start with PPB/')
        return value

    def create(self, validated_data):
        validated_data.setdefault('status', 'draft')
        return super().create(validated_data)


class RegistrationStep2Serializer(serializers.ModelSerializer):
    """Step 2: Pharmacist personal details and credentials."""

    class Meta:
        model  = PharmacyRegistration
        fields = [
            'pharmacist_name', 'id_or_passport_no', 'pharmacist_reg_no',
            'practicing_license', 'practicing_expiry',
            'pharmacist_phone', 'pharmacist_email',
            'id_document', 'practicing_license_doc',
        ]


class RegistrationStep3Serializer(serializers.ModelSerializer):
    """Step 3: Business document uploads."""

    class Meta:
        model  = PharmacyRegistration
        fields = [
            'operating_license_doc', 'business_reg_cert',
            'kra_pin_cert', 'proof_of_address_doc',
        ]


class RegistrationStep4Serializer(serializers.ModelSerializer):
    """Step 4: Financial setup. Password triggers final user creation in the view."""
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model  = PharmacyRegistration
        fields = [
            'mpesa_method', 'short_code_name', 'short_code_number',
            'settlement_bank', 'settlement_frequency',
            'password',
        ]

    def validate_short_code_number(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError('Short code must contain only digits')
        if value and len(value) != 6:
            raise serializers.ValidationError('Short code must be exactly 6 digits')
        return value

    def validate_password(self, value):
        if value and len(value) < 8:
            raise serializers.ValidationError('Password must be at least 8 characters')
        return value

    def update(self, instance, validated_data):
        validated_data.pop('password', None)  # handled by view
        return super().update(instance, validated_data)


# =============================================================================
# SINGLE-STEP COMPLETE REGISTRATION
# Used by POST /api/auth/register/complete/
# All 4 steps combined into one request.
# =============================================================================

class CompleteRegistrationSerializer(serializers.ModelSerializer):
    """
    Combines all registration steps into one multipart/form-data POST.

    Required fields: pharmacy_name_legal, business_reg_no, kra_pin,
                     ppb_license_no, license_expiry, county, physical_address,
                     business_phone, business_email, password

    All document fields and financial fields are optional.
    """
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    # Optional overrides
    trading_name           = serializers.CharField(required=False, allow_blank=True, default='')
    gps_lat                = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    gps_lng                = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    pharmacist_name        = serializers.CharField(required=False, allow_blank=True, default='')
    id_or_passport_no      = serializers.CharField(required=False, allow_blank=True, default='')
    pharmacist_reg_no      = serializers.CharField(required=False, allow_blank=True, default='')
    practicing_license     = serializers.CharField(required=False, allow_blank=True, default='')
    practicing_expiry      = serializers.DateField(required=False, allow_null=True)
    pharmacist_phone       = serializers.CharField(required=False, allow_blank=True, default='')
    pharmacist_email       = serializers.EmailField(required=False, allow_blank=True, default='')
    id_document            = serializers.FileField(required=False, allow_null=True)
    practicing_license_doc = serializers.FileField(required=False, allow_null=True)
    operating_license_doc  = serializers.FileField(required=False, allow_null=True)
    business_reg_cert      = serializers.FileField(required=False, allow_null=True)
    kra_pin_cert           = serializers.FileField(required=False, allow_null=True)
    proof_of_address_doc   = serializers.FileField(required=False, allow_null=True)
    mpesa_method           = serializers.ChoiceField(choices=['PAYBILL', 'TILL'], required=False, allow_null=True)
    short_code_name        = serializers.CharField(required=False, allow_blank=True, default='')
    short_code_number      = serializers.CharField(required=False, allow_blank=True, default='')
    settlement_bank        = serializers.CharField(required=False, allow_blank=True, default='')
    settlement_frequency   = serializers.ChoiceField(
        choices=['DAILY', 'WEEKLY', 'MONTHLY'], required=False, default='DAILY'
    )

    class Meta:
        model  = PharmacyRegistration
        fields = [
            # Step 1 — required
            'pharmacy_name_legal', 'trading_name',
            'business_reg_no', 'kra_pin',
            'ppb_license_no', 'license_expiry',
            'county', 'sub_county', 'physical_address',
            'gps_lat', 'gps_lng',
            'business_phone', 'business_email',
            # Step 2 — optional
            'pharmacist_name', 'id_or_passport_no', 'pharmacist_reg_no',
            'practicing_license', 'practicing_expiry',
            'pharmacist_phone', 'pharmacist_email',
            'id_document', 'practicing_license_doc',
            # Step 3 — optional
            'operating_license_doc', 'business_reg_cert',
            'kra_pin_cert', 'proof_of_address_doc',
            # Step 4 — optional
            'mpesa_method', 'short_code_name', 'short_code_number',
            'settlement_bank', 'settlement_frequency',
            # Auth
            'password',
        ]

    def validate_kra_pin(self, value):
        import re
        v = value.upper()
        if not re.match(r'^[A-Z]\d{9}[A-Z]$', v):
            raise serializers.ValidationError(
                'Invalid KRA PIN. Format: one letter + 9 digits + one letter. e.g. A004626956Z'
            )
        return v

    def validate_ppb_license_no(self, value):
        if value and not value.startswith('PPB/'):
            raise serializers.ValidationError('PPB License must start with PPB/')
        return value

    def validate_short_code_number(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError('Short code must contain only digits')
        if value and len(value) != 6:
            raise serializers.ValidationError('Short code must be exactly 6 digits')
        return value

    def create(self, validated_data):
        validated_data.pop('password', None)  # password handled by view
        validated_data['current_step'] = 5
        validated_data['status']       = 'submitted'
        validated_data['submitted_at'] = timezone.now()
        return super().create(validated_data)
