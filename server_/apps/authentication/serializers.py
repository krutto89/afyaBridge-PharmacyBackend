# apps/authentication/serializers.py

from rest_framework import serializers

from django.contrib.auth import authenticate
from .models import PharmacyUser, NotificationPreference, PharmacyRegistration
from django.contrib.auth import get_user_model
User = get_user_model()

from datetime import timedelta
from django.utils import timezone


from .models import (
    PharmacyUser, 
    PharmacyRegistration, 
    OTPVerification, 
    PasswordReset
)


# ====================== AUTH SERIALIZERS ======================

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user = PharmacyUser.objects.get(email=data['email'])
            if not user.check_password(data['password']):
                raise serializers.ValidationError("Invalid credentials")
            data['user'] = user
            return data
        except PharmacyUser.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyUser
        fields = [
            'id',
            'email',
            'full_name',
            'phone_number',
            'role',
            'pharmacy_id',
        ]

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)


# ====================== REGISTRATION STEP SERIALIZERS ======================

class NotificationPrefSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationPreference
        fields = '__all__'
        read_only_fields = ['id', 'user', 'updated_at']


class RegistrationStep1Serializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyRegistration
        fields = [
            'pharmacy_name_legal', 
            'business_email', 
            'business_phone', 
            'pharmacist_name', 
            'physical_address', 
            'county', 
            'sub_county'
        ]

    def create(self, validated_data):
        validated_data.setdefault('license_expiry', timezone.now().date() + timedelta(days=730))
        validated_data.setdefault('ppb_license_no', '')
        validated_data.setdefault('status', 'draft')
        return super().create(validated_data)


class RegistrationStep2Serializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyRegistration
        fields = ['ppb_license_no', 'license_expiry']

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.current_step = 2
        instance.save()
        return instance


class RegistrationStep3Serializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyRegistration
        fields = []

    def update(self, instance, validated_data):
        instance.current_step = 3
        instance.save()
        return instance


# apps/authentication/serializers.py

class RegistrationStep4Serializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    
    # Add fields you want to capture from step 4
    security_question = serializers.CharField(required=False, allow_blank=True)
    security_answer = serializers.CharField(required=False, allow_blank=True)
    two_factor_enabled = serializers.BooleanField(required=False, default=True)
    licensing_affirmed = serializers.BooleanField(required=False)
    dpa_consent = serializers.BooleanField(required=False)
    verification_consent = serializers.BooleanField(required=False)
    terms_privacy_accepted = serializers.BooleanField(required=False)

    class Meta:
        model = PharmacyRegistration
        fields = [
            'password', 'security_question', 'security_answer',
            'two_factor_enabled', 'licensing_affirmed', 'dpa_consent',
            'verification_consent', 'terms_privacy_accepted'
        ]

    def update(self, instance, validated_data):
        # Pop password before updating model fields
        password = validated_data.pop('password', None)
        
        # Update any other fields that exist on the model
        for attr, value in validated_data.items():
            if hasattr(instance, attr):
                setattr(instance, attr, value)

        instance.current_step = 4
        instance.save()

        # Store password temporarily if provided (but you already handle it in the view)
        if password:
            # You can store it encrypted somewhere if needed, but view already uses it
            pass

        return instance
# ====================== OTP SERIALIZER ======================

class OTPVerifySerializer(serializers.Serializer):

    phone    = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=6, min_length=6)
    class Meta:
        model  = PharmacyRegistration
        fields = [
            'id', 'pharmacy_name_legal', 'trading_name',
            'business_reg_no', 'kra_pin', 'ppb_license_no', 'license_expiry',
            'county', 'sub_county', 'physical_address', 'gps_lat', 'gps_lng',
            'business_phone', 'business_email',
        ]

    def validate_kra_pin(self, value):
        # A00XXXXXXXZ
        import re
        if not re.match(r'^[A-Z]\d{9}[A-Z]$', value):
            raise serializers.ValidationError(
                'Invalid KRA PIN format. Expected: A00XXXXXXXZ'
            )
        return value

    def validate_ppb_license_no(self, value):
        if not value.startswith('PPB/'):
            raise serializers.ValidationError(
                'PPB License must start with PPB/'
            )
        return value


class RegistrationStep2Serializer(serializers.ModelSerializer):
    class Meta:
        model  = PharmacyRegistration
        fields = [
            'pharmacist_name', 'id_or_passport_no', 'pharmacist_reg_no',
            'practicing_license', 'practicing_expiry',
            'pharmacist_phone', 'pharmacist_email',
            'id_document', 'practicing_license_doc',
        ]


class RegistrationStep3Serializer(serializers.ModelSerializer):
    class Meta:
        model  = PharmacyRegistration
        fields = [
            'operating_license_doc', 'business_reg_cert',
            'kra_pin_cert', 'proof_of_address_doc',
        ]


class RegistrationStep4Serializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model  = PharmacyRegistration
        fields = [
            'mpesa_method', 'short_code_name',
            'short_code_number', 'settlement_bank', 'settlement_frequency',
            'password',
        ]

    def validate_short_code_number(self, value):
        if value and len(value) != 6:
            raise serializers.ValidationError('Short code must be exactly 6 digits')
        return value

    def validate_password(self, value):
        if value and len(value) < 8:
            raise serializers.ValidationError('Password must be at least 8 characters')
        return value



    phone = serializers.CharField()
    otp_code = serializers.CharField()


# ====================== FULL REGISTRATION SERIALIZER ======================

class FullPharmacyRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = PharmacyRegistration
        fields = '__all__'

    def validate(self, data):
        if data.get('password') and not data.get('business_email'):
            raise serializers.ValidationError({
                "business_email": "Business email is required when providing password."
            })
        return data

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        
        validated_data['current_step'] = 5
        validated_data['status'] = 'draft'
        validated_data['submitted_at'] = timezone.now()

        registration = super().create(validated_data)

        if password:
            registration.status = 'APPROVED'
            registration.save()


        return registration