from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from django.utils import timezone
from datetime import timedelta
import random
import string
import requests
import os

from django.contrib.auth.hashers import make_password

from .models import PharmacyUser, PharmacyRegistration, OTPVerification, PasswordReset
from apps.settings_module.models import Pharmacy
import utils.responses as resp


def _link_user_to_pharmacy(user, pharmacy):
    """
    Safely link a user to a pharmacy using a targeted SQL UPDATE.
    This avoids foreign key constraint errors that occur with direct field assignment + save().
    """
    PharmacyUser.objects.filter(id=user.id).update(pharmacy_id=pharmacy.id)
    user.refresh_from_db()


# ========================== AUTH VIEWS ==========================

class RegisterUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        try:
            user = PharmacyUser.objects.create(
                email        = data['email'],
                full_name    = data['full_name'],
                role         = data['role'],
                phone_number = data.get('phone_number'),
                password     = make_password(data['password']),
            )
            return resp.created({"id": str(user.id), "email": user.email}, "User registered successfully")
        except Exception as e:
            return resp.error("Registration failed", str(e))


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        from .serializers import LoginSerializer, UserProfileSerializer
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return resp.error('Login failed', serializer.errors)
        user    = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return resp.success({
            'access_token':  str(refresh.access_token),
            'refresh_token': str(refresh),
            'user':          UserProfileSerializer(user, context={'request': request}).data,
        }, 'Login successful')


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return resp.error('Refresh token is required')
        try:
            RefreshToken(refresh_token).blacklist()
            return resp.success(message='Logged out successfully')
        except TokenError:
            return resp.error('Invalid or expired token')


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .serializers import UserProfileSerializer
        return resp.success(UserProfileSerializer(request.user, context={'request': request}).data)

    def put(self, request):
        from .serializers import UserProfileSerializer
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return resp.success(serializer.data, 'Profile updated')
        return resp.error('Validation failed', serializer.errors)


class ProfilePhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        photo = request.FILES.get('photo')
        if not photo:
            return resp.error('No photo provided')
        if photo.size > 800 * 1024:
            return resp.error('Photo must be under 800KB')
        request.user.photo = photo
        request.user.save()
        from .serializers import UserProfileSerializer
        return resp.success(UserProfileSerializer(request.user, context={'request': request}).data, 'Photo updated')

    def delete(self, request):
        request.user.photo = None
        request.user.save()
        return resp.success(message='Photo removed')


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        from .serializers import ChangePasswordSerializer
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return resp.error('Validation failed', serializer.errors)
        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return resp.error('Current password is incorrect')
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return resp.success(message='Password changed')


# ========================== REGISTRATION STEP VIEWS ==========================

class RegistrationStep1View(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        from .serializers import RegistrationStep1Serializer
        serializer = RegistrationStep1Serializer(data=request.data)
        if not serializer.is_valid():
            return resp.error('Step 1 validation failed', serializer.errors)
        registration = serializer.save(current_step=1, status='draft')
        return resp.created({
            'registration_id': str(registration.id),
            'current_step':    1,
            'next_step':       2,
        }, 'Step 1 saved')


class RegistrationStep2View(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request, registration_id):
        from .serializers import RegistrationStep2Serializer
        try:
            reg = PharmacyRegistration.objects.get(id=registration_id)
        except PharmacyRegistration.DoesNotExist:
            return resp.not_found('Registration not found')
        serializer = RegistrationStep2Serializer(reg, data=request.data, partial=True)
        if not serializer.is_valid():
            return resp.error('Step 2 validation failed', serializer.errors)
        serializer.save(current_step=2)
        return resp.success({'registration_id': str(reg.id), 'current_step': 2, 'next_step': 3}, 'Step 2 saved successfully')


class RegistrationStep3View(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request, registration_id):
        from .serializers import RegistrationStep3Serializer
        try:
            reg = PharmacyRegistration.objects.get(id=registration_id)
        except PharmacyRegistration.DoesNotExist:
            return resp.not_found('Registration not found')
        serializer = RegistrationStep3Serializer(reg, data=request.data, partial=True)
        if not serializer.is_valid():
            return resp.error('Step 3 validation failed', serializer.errors)
        serializer.save(current_step=3)
        return resp.success({'current_step': 3, 'next_step': 4}, 'Documents uploaded')


class RegistrationStep4View(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def put(self, request, registration_id):
        from .serializers import RegistrationStep4Serializer, UserProfileSerializer
        try:
            reg = PharmacyRegistration.objects.get(id=registration_id)
        except PharmacyRegistration.DoesNotExist:
            return resp.not_found('Registration not found')

        serializer = RegistrationStep4Serializer(reg, data=request.data, partial=True)
        if not serializer.is_valid():
            return resp.error('Step 4 validation failed', serializer.errors)

        reg = serializer.save(current_step=4)

        # Phase 2: final submission (password provided)
        password = serializer.validated_data.get('password')

        if password:
            try:
                reg.current_step = 5
                reg.status = 'APPROVED'
                reg.submitted_at = timezone.now()
                reg.save()

                pharmacy, _ = Pharmacy.objects.get_or_create(
                    name=reg.pharmacy_name_legal,
                    defaults={
                        'email':          reg.business_email,
                        'phone':          reg.business_phone or '',
                        'address_line1':  reg.physical_address or '',
                        'county':         reg.county or '',
                        'sub_county':     reg.sub_county or '',
                        'gps_lat':        reg.gps_lat,
                        'gps_lng':        reg.gps_lng,
                        'license_number': reg.ppb_license_no or '',
                        'license_expiry': reg.license_expiry,
                    },
                )

                user, _ = PharmacyUser.objects.get_or_create(
                    email=reg.business_email,
                    defaults={
                        'full_name': reg.pharmacist_name or reg.pharmacy_name_legal,
                        'role':      'pharmacist',
                    }
                )

                # Link pharmacy safely
                _link_user_to_pharmacy(user, pharmacy)

                user.set_password(password)
                user.save()

                refresh = RefreshToken.for_user(user)
                return resp.success({
                    'registration_id': str(reg.id),
                    'status':          'APPROVED',
                    'access_token':    str(refresh.access_token),
                    'refresh_token':   str(refresh),
                    'user':            UserProfileSerializer(user, context={'request': request}).data,
                }, 'Registration completed successfully')

            except Exception as e:
                return resp.error("Failed to complete registration", str(e))

        # If no password yet, just save step 4
        return resp.success({
            'registration_id': str(reg.id),
            'current_step':    4,
            'message':         'Step 4 saved',
        }, 'Step 4 saved successfully')


class RegistrationStatusView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, registration_id):
        try:
            reg = PharmacyRegistration.objects.get(id=registration_id)
        except PharmacyRegistration.DoesNotExist:
            return resp.not_found('Registration not found')
        return resp.success({
            'registration_id': str(reg.id),
            'pharmacy_name':   reg.pharmacy_name_legal,
            'status':          reg.status,
            'current_step':    reg.current_step,
        })


# ========================== OTP & PASSWORD VIEWS ==========================

class SendOTPView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return resp.error('Email is required')

        admin_auth_url = os.environ.get('ADMIN_AUTH_URL', '').rstrip('/')
        if not admin_auth_url:
            return resp.error('ADMIN_AUTH_URL is not configured')

        try:
            response = requests.post(
                url     = f"{admin_auth_url}/api/admin/auth/send-otp",
                json    = {'email': email},
                headers = {'Content-Type': 'application/json'},
                timeout = 10,
            )
            body = response.json()
            if not response.ok:
                return resp.error(body.get('message', 'Failed to send OTP'))
            return resp.success(body.get('data', body), body.get('message', 'OTP sent successfully'))
        except Exception as e:
            return resp.error(f'Failed to send OTP: {str(e)}')


class VerifyOTPView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        from .serializers import OTPVerifySerializer
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return resp.error('Invalid request', serializer.errors)
        phone    = serializer.validated_data['phone']
        otp_code = serializer.validated_data['otp_code']
        try:
            otp = OTPVerification.objects.get(phone=phone, otp_code=otp_code, is_used=False, expires_at__gt=timezone.now())
            otp.is_used = True
            otp.save()
            PharmacyRegistration.objects.filter(business_phone=phone).update(phone_verified=True)
            return resp.success({'phone_verified': True}, 'Phone verified successfully')
        except OTPVerification.DoesNotExist:
            return resp.error('Invalid or expired OTP')


class ForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return resp.error('Email is required')
        try:
            user = PharmacyUser.objects.get(email=email)
        except PharmacyUser.DoesNotExist:
            return resp.success({'message': 'If an account exists, you will receive a reset link.'}, 'Email sent')

        token   = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
        expires = timezone.now() + timedelta(hours=1)
        PasswordReset.objects.create(user=user, token=token, expires_at=expires)
        reset_url = f"http://localhost:5173/auth/reset-password?token={token}"
        return resp.success({
            'message':   'If an account exists, you will receive a reset link.',
            'reset_url': reset_url,
            'token':     token,
        }, 'Password reset email sent')


class ResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token    = request.data.get('token', '')
        password = request.data.get('password', '')
        if not token or not password:
            return resp.error('Token and password are required')
        if len(password) < 8:
            return resp.error('Password must be at least 8 characters')
        try:
            reset = PasswordReset.objects.get(token=token, is_used=False)
        except PasswordReset.DoesNotExist:
            return resp.error('Invalid or expired reset token')
        if reset.expires_at < timezone.now():
            return resp.error('Reset token has expired')
        user = reset.user
        user.set_password(password)
        user.save()
        reset.is_used = True
        reset.save()
        return resp.success({'message': 'Password has been reset successfully.'}, 'Password reset successful')


# ========================== COMPLETE REGISTRATION (single-step) ==========================

class CompletePharmacyRegistrationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from .serializers import FullPharmacyRegistrationSerializer, UserProfileSerializer

        serializer = FullPharmacyRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return resp.error('Registration validation failed', serializer.errors)

        registration = serializer.save()
        password     = request.data.get('password')

        if password:
            try:
                pharmacy, _ = Pharmacy.objects.get_or_create(
                    name=registration.pharmacy_name_legal,
                    defaults={
                        'email':          registration.business_email,
                        'phone':          getattr(registration, 'business_phone', '') or '',
                        'address_line1':  getattr(registration, 'physical_address', '') or '',
                        'county':         getattr(registration, 'county', '') or '',
                        'sub_county':     getattr(registration, 'sub_county', '') or '',
                        'gps_lat':        getattr(registration, 'gps_lat', None),
                        'gps_lng':        getattr(registration, 'gps_lng', None),
                        'license_number': getattr(registration, 'ppb_license_no', '') or '',
                        'license_expiry': getattr(registration, 'license_expiry', None),
                    }
                )

                user, _ = PharmacyUser.objects.get_or_create(
                    email=registration.business_email,
                    defaults={
                        'full_name': getattr(registration, 'pharmacist_name', '') or registration.pharmacy_name_legal,
                        'role':      'pharmacist',
                    }
                )

                # Update name/phone if changed
                if getattr(registration, 'pharmacist_name', None):
                    user.full_name = registration.pharmacist_name
                if getattr(registration, 'business_phone', None):
                    user.phone_number = registration.business_phone
                user.save()

                # Link pharmacy safely
                _link_user_to_pharmacy(user, pharmacy)

                user.set_password(password)
                user.save()

                refresh = RefreshToken.for_user(user)
                return resp.success({
                    'registration_id': str(registration.id),
                    'status':          'APPROVED',
                    'message':         'Registration completed successfully!',
                    'access_token':    str(refresh.access_token),
                    'refresh_token':   str(refresh),
                    'user':            UserProfileSerializer(user, context={'request': request}).data,
                }, 'Registration successful')

            except Exception as e:
                return resp.error("Failed to complete registration", str(e))

        return resp.success({
            'registration_id': str(registration.id),
            'current_step':    registration.current_step,
            'status':          registration.status,
            'message':         'Registration data saved successfully',
        }, 'Registration saved')