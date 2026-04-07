# apps/authentication/urls.py

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication
    path('login/',            views.LoginView.as_view(),          name='auth-login'),
    path('register/user/',    views.RegisterUserView.as_view(),   name='register-user'),
    path('logout/',           views.LogoutView.as_view(),         name='auth-logout'),
    path('token/refresh/',    TokenRefreshView.as_view(),         name='token-refresh'),

    # Profile
    path('profile/',          views.ProfileView.as_view(),        name='auth-profile'),
    path('profile/photo/',    views.ProfilePhotoView.as_view(),   name='auth-photo'),
    path('change-password/',  views.ChangePasswordView.as_view(), name='auth-change-pw'),

    # Multi-step Registration (Old - kept for compatibility)
    path('register/step1/',               views.RegistrationStep1View.as_view(), name='register-step1'),
    path('register/<uuid:registration_id>/step2/', views.RegistrationStep2View.as_view(), name='register-step2'),
    path('register/<uuid:registration_id>/step3/', views.RegistrationStep3View.as_view(), name='register-step3'),
    path('register/<uuid:registration_id>/step4/', views.RegistrationStep4View.as_view(), name='register-step4'),
    path('register/<uuid:registration_id>/status/', views.RegistrationStatusView.as_view(), name='register-status'),

    # NEW: Single Complete Registration (Recommended for React)
    path('register/complete/', views.CompletePharmacyRegistrationView.as_view(), name='register-complete'),

    # OTP
    path('otp/send/', views.SendOTPView.as_view(), name='otp-send'),
    path('otp/verify/', views.VerifyOTPView.as_view(), name='otp-verify'),

    # Password Reset
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
]