
from django.urls import path
from . import views

urlpatterns = [
    path('',
        views.PrescriptionListView.as_view(),
        name='prescription-list'),

    path('<uuid:rx_id>/',
        views.PrescriptionDetailView.as_view(),
        name='prescription-detail'),

    path('<uuid:rx_id>/validate/',
        views.ValidatePrescriptionView.as_view(),
        name='prescription-validate'),

    path('<uuid:rx_id>/reject/',
        views.RejectPrescriptionView.as_view(),
        name='prescription-reject'),

    path('<uuid:rx_id>/dispense/',
        views.DispensePrescriptionView.as_view(),
        name='prescription-dispense'),
]