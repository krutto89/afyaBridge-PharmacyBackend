# apps/patients/urls.py
from django.urls import path
from . import views

urlpatterns = [

    # ── Prescriptions & Refills ──────────────────────────
    path('prescriptions/refillable/',
        views.RefillablePrescriptionsView.as_view(),
        name='refillable-prescriptions'),

    path('prescriptions/select/',
        views.SelectPrescriptionView.as_view(),
        name='select-prescription'),

    path('prescriptions/pharmacy/select/',
        views.SelectPharmacyView.as_view(),
        name='select-pharmacy'),

    path('prescriptions/refill/',
        views.InitiateRefillView.as_view(),
        name='initiate-refill'),

    path('prescriptions/refill/<uuid:refill_id>/location/',
        views.SetDeliveryLocationView.as_view(),
        name='refill-location'),

    # ── Pharmacy Search ───────────────────────────────────
    path('pharmacies/nearby/',
        views.NearbyPharmaciesView.as_view(),
        name='pharmacies-nearby'),

    path('pharmacies/search/',
        views.PharmacySearchView.as_view(),
        name='pharmacies-search'),

    path('pharmacies/map/',
        views.PharmacyMapView.as_view(),
        name='pharmacies-map'),

    # ── Orders & Payments ─────────────────────────────────
    path('orders/<uuid:refill_id>/summary/',
        views.OrderSummaryView.as_view(),
        name='order-summary'),

    path('orders/<uuid:refill_id>/pay/',
        views.PayOrderView.as_view(),
        name='order-pay'),

    path('orders/<uuid:refill_id>/confirmation/',
        views.OrderConfirmationView.as_view(),
        name='order-confirmation'),

    # ── M-Pesa ────────────────────────────────────────────
    path('payments/mpesa/callback/',
        views.MpesaCallbackView.as_view(),
        name='mpesa-callback'),

    path('payments/<uuid:transaction_id>/status/',
        views.PaymentStatusView.as_view(),
        name='payment-status'),

    # ── Patient Dashboard ─────────────────────────────────
    path('meds/dashboard/',
        views.PatientMedDashboardView.as_view(),
        name='med-dashboard'),
]